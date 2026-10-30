"""Manual, bounded screen caller. Default is a plan; no training/submission API."""
import argparse
import copy
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'research/software-function-caller-20261029'))
from failure_diagnostics import safe_failure

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'integrations/openenv-arena'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def modules():
    sys.path[:0] = [str(ROOT / p) for p in (
        'research/software-retain-public-passing-20261030',
        'research/software-function-trial-20261029')]
    import feedback_protocol
    return feedback_protocol, feedback_protocol.Trial


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked_inputs(bundle, expected):
    protocol, _ = modules()
    if protocol.digest(bundle) != expected or bundle != protocol.bundle(bundle['chunk']):
        raise ValueError('exact new screen plan required')
    return bundle['screen_jobs']


def record(stream, value):
    stream.write(json.dumps(value, allow_nan=False) + '\n')
    stream.flush()
    os.fsync(stream.fileno())


def phase(bundle, expected, output, backend, counter, deadline):
    """Two assigned attempts per bounded chunk; full eight-attempt study admitted."""
    protocol, Trial = modules()
    jobs = checked_inputs(bundle, expected)
    if output.exists(): raise ValueError('fresh archive required; no resume/redraw')
    backend.admit([28672]*16, 8096, deadline)
    output.mkdir(mode=0o700)
    rows=[];identities=set();stopped=False
    with (output/'events.jsonl').open('x') as events, (output/'records.jsonl').open('x') as records:
        for job in jobs:
            frozen=protocol.capture(job)
            row=dict(job,prompt_sha256=frozen['prompt_sha256'],problem_sha256=frozen['problem_sha256'],
                call_id=None,response_id=None,reservation_label=None,call_ids=[],response_ids=[],reservation_labels=[],
                generation_tokens=0,observation_tokens=0,finish_reason=None,terminal_reward_observed=None,
                semantic_reward=None,category='budget',max_context=0,turns=0)
            if stopped or time.monotonic()>=deadline:
                stopped=True;record(records,row);rows.append(row);continue
            trial=Trial(job)
            if trial.messages!=frozen['messages']:raise ValueError('first native prompt changed')
            attempt_deadline=min(deadline,time.monotonic()+600)
            for turn in range(2):
                remaining=8192-row['generation_tokens']-row['observation_tokens']-96
                limit=min(6000 if turn==0 else 8096,remaining)
                if limit<=0 or time.monotonic()>=attempt_deadline or counter.context(trial.messages)+limit+96>24576:
                    row.update(category='budget',semantic_reward=None);stopped=True;break
                payload=dict(protocol.sampling_for(job,trial.turn),messages=copy.deepcopy(trial.messages),max_tokens=limit)
                label=job['attempt_id']+':'+str(turn)
                record(events,dict(event='intent',attempt_id=job['attempt_id'],label=label,turn=turn,max_tokens=limit,
                    request_sha256=protocol.digest(payload),messages_sha256=protocol.digest(payload['messages'])))
                started=time.monotonic();stage='reservation'
                try:
                    backend.reserve(label,28672,limit,attempt_deadline)
                    row['reservation_labels'].append(label);row['reservation_label']=row['reservation_labels'][0]
                    record(events,dict(event='reserved',attempt_id=job['attempt_id'],label=label,turn=turn))
                    stage='provider';row['call_ids'].append(label);row['call_id']=row['call_ids'][0]
                    record(events,dict(event='calling',attempt_id=job['attempt_id'],call_id=label,turn=turn))
                    response=backend.call(payload,min(360,attempt_deadline-time.monotonic()),job)
                    stage='response_validation';backend.check_reply(response)
                    identity=response.get('id')
                    if not isinstance(identity,str) or not identity:raise ValueError('response identity required')
                    identity=hashlib.sha256(identity.encode()).hexdigest()
                    if identity in identities:raise ValueError('reused response identity')
                    identities.add(identity)
                    record(events,dict(event='response',attempt_id=job['attempt_id'],turn=turn,response=response))
                    usage=response.get('usage',{})
                    if any(type(usage.get(k)) is not int or usage[k]<0 for k in ('prompt_tokens','completion_tokens')):raise ValueError('verified usage required')
                    row['response_ids'].append(identity);row['response_id']=hashlib.sha256(protocol.canonical(row['response_ids']).encode()).hexdigest()
                    row['generation_tokens']+=usage['completion_tokens'];row['turns']+=1
                    row['max_context']=max(row['max_context'],usage['prompt_tokens']+usage['completion_tokens'])
                    if usage['prompt_tokens']>28672 or usage['completion_tokens']>limit:
                        row.update(category='budget',semantic_reward=None);stopped=True;break
                    if row['max_context']>24576:
                        row.update(category='budget',semantic_reward=None);stopped=True;break
                    choices=response['choices']
                    if not isinstance(choices,list) or len(choices)!=1:raise ValueError('one response choice required')
                    choice=choices[0];message=choice['message'];backend.check_message(message)
                    row['finish_reason']=choice.get('finish_reason')
                    if row['finish_reason']=='length':row.update(category='truncation');break
                    if row['finish_reason']!='stop':row.update(category='provider');stopped=True;break
                    stage='native_processing';value=trial.consume(message.get('content'))
                    obs=counter.count(protocol.canonical(trial.native[-1])) if trial.native and len(trial.native)==turn+1 else 0
                    row['observation_tokens']+=obs
                    row['max_context']=max(row['max_context'],counter.context(trial.messages),usage['prompt_tokens']+usage['completion_tokens']+obs)
                    if row['generation_tokens']+row['observation_tokens']>8192 or row['max_context']>24576:
                        row.update(category='budget',semantic_reward=None);stopped=True;break
                    row.update(category=value['category'],terminal_reward_observed=value['native_reward'],semantic_reward=value.get('semantic_reward'))
                    if value['done']:break
                except Exception as exc:
                    record(events,dict(event='failure',attempt_id=job['attempt_id'],turn=turn,**safe_failure(exc,stage,time.monotonic()-started)))
                    # Any called turn lacking a fully validated response/usage is unknown,
                    # even if an earlier turn's cost is known. Preserve its reservation.
                    if len(row['call_ids'])>row['turns']:row['generation_tokens']=None
                    category='execution' if stage=='native_processing' else 'budget' if stage=='reservation' else 'provider'
                    row.update(category=category,semantic_reward=None)
                    stopped=True;break
            if row['category']=='awaiting_revision':row.update(category='budget',semantic_reward=None);stopped=True
            record(records,row);rows.append(row)
    summary=dict(assigned_attempts=2,recorded_attempts=len(rows),observed_calls=sum(len(r['call_ids']) for r in rows),
        source_inputs_sha256=expected,scripted=backend.scripted,is_training=False,model_improvement=False,
        arena_wrapper_equivalent=False,thinking_verified=False,fresh_model_confirmation=False)
    (output/'complete.json').write_text(json.dumps(summary,indent=2)+'\n')
    return rows


def reconciliation(path, receipt):
    """Read an externally completed private audit; never refresh/write it."""
    value = json.loads(path.read_text())
    now = datetime.now(timezone.utc)
    def fresh(text):
        return 0 <= (now-datetime.fromisoformat(text)).total_seconds() <= 7200
    if (not fresh(value['observed_at']) or value.get('execution_authorized') is not True or
            value.get('receipt_inventory_complete') is not True or
            value.get('root_prior_not_reattested') is not False or
            any(value.get(k) for k in ('errors', 'changed_files', 'carry_forward_errors'))):
        raise ValueError('fresh complete reconciled existing allocation required')
    billing = value['actual_billing_visual']
    if not fresh(billing['observed_at']) or billing['automatic_recharge'] not in (False, 'OFF', 'off'):
        raise ValueError('fresh actual billing observation required')
    known = value['all_known_receipts']
    inventory = value['inventory']
    known_paths = {str(Path(item['receipt']).resolve()) for item in known}
    inventory_paths = {str(Path(item['path']).resolve()) for item in inventory}
    if (not known or len(known_paths) != len(known) or
            len(inventory_paths) != len(inventory) or known_paths != inventory_paths):
        raise ValueError('complete nonduplicated audited receipt inventory required')
    for item in inventory:
        if sha(item['path']) != item['sha256']:
            raise ValueError('audited inventory changed')
    selected = False
    for item in known:
        p = Path(item['receipt']); ledger = p.with_suffix('.reservations.jsonl')
        if sha(p) != item['receipt_sha256'] or sha(ledger) != item['ledger_sha256']:
            raise ValueError('receipt or ledger differs from reconciliation')
        selected |= p.resolve() == receipt.resolve()
    if not selected:
        raise ValueError('current receipt not in audited inventory')
    return Decimal(str(billing['credits_usd']))


class LiveBackend:
    scripted = False
    def __init__(self, receipt, audit, tokenizer, amendment_sha256):
        self.credit = reconciliation(audit, receipt)
        self.base = load('frozen_software_caller_base', ROOT/'scripts/repair-signal-screen.py')
        selected = next(x for x in json.loads(audit.read_text())['all_known_receipts']
                        if Path(x['receipt']).resolve() == receipt.resolve())
        self.budget = self.base.DollarReservations(receipt, amendment_sha256=amendment_sha256,
            receipt_sha256=selected['receipt_sha256'], ledger_sha256=selected['ledger_sha256'])
        self.counter = self.base.helper.load_counter(argparse.Namespace(accounting='arena', tokenizer_json=tokenizer, tokenizer_sha256=self.base.TOKENIZER_SHA))
        self.token = os.environ.get('HF_TOKEN', '')
        if not self.token:
            raise ValueError('existing environment credential required')
        self.opener = self.base.urllib.request.build_opener(self.base.helper.NoRedirect(), self.base.urllib.request.ProxyHandler({}))
        self.frozen = self.base.quote(self.opener, self.token)
    def admit(self, bounds, generation, deadline):
        rows = [json.loads(x) for x in self.budget.ledger.read_text().splitlines() if x]
        remaining = self.budget.cap-sum((Decimal(x['usd']) for x in rows), Decimal(0))
        module = load('whole_phase_admission', ROOT/'scripts/stage-phase-admission.py')
        quote = module.admit(16, bounds, generation, self.frozen['provider']['pricing'], min(remaining, self.credit))
        if not quote['admitted'] or time.monotonic() >= deadline:
            raise ValueError('complete phase cannot fit existing allocation/deadline')
    def reserve(self, label, prompt, generation, deadline):
        timeout = self.base.request_timeout(deadline, 15)
        if self.base.quote(self.opener, self.token, timeout) != self.frozen:
            raise ValueError('selected route metadata changed')
        self.base.request_timeout(deadline, 180)
        return self.budget.reserve(label, prompt, generation, self.frozen['provider']['pricing'])
    def call(self, payload, timeout, job):
        stream = load('helper4000_stream', ROOT/'scripts/provider_stream.py')
        return stream.provider_call(self.opener, self.base.BASE, self.token, payload, timeout)
    def check_reply(self, response):
        if self.token in json.dumps(response, allow_nan=False):
            raise ValueError('credential leakage guard')
    def check_message(self, message):
        _, _, _, _, error, leaked = self.base.helper.reasoning_payload(message, self.token)
        if error or leaked or message.get('tool_calls') or message.get('function_call'):
            raise ValueError('invalid provider message')


def execute(deadline, args):
    bundle = json.loads(args.inputs.read_text())
    protocol,_=modules()
    checked_inputs(bundle,args.inputs_sha256)
    if len(args.prior)!=bundle['chunk']:raise ValueError('all earlier chunks required; no resume or skip')
    for index,path in enumerate(args.prior):
        prior=protocol.bundle(index);complete=json.loads((path/'complete.json').read_text())
        rows=[json.loads(x) for x in (path/'records.jsonl').read_text().splitlines()]
        if (complete.get('scripted') is not False or complete.get('assigned_attempts')!=2
                or complete.get('recorded_attempts')!=2 or not 2<=complete.get('observed_calls',0)<=4
                or complete.get('source_inputs_sha256')!=protocol.digest(prior)
                or len(rows)!=2 or [r['attempt_id'] for r in rows]!=[j['attempt_id'] for j in prior['screen_jobs']]
                or any(r['generation_tokens'] is None or r['category'] in ['provider','budget'] for r in rows)):
            raise ValueError('incomplete or unknown-usage earlier chunk; experiment remains inconclusive')
    backend = LiveBackend(args.receipt, args.reconciliation, args.tokenizer, args.amendment_sha256)
    phase(bundle, args.inputs_sha256, args.output, backend, backend.counter, deadline)
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute', action='store_true')
    p.add_argument('--prior',type=Path,nargs='*',default=[])
    for key in ('inputs', 'receipt', 'reconciliation', 'tokenizer', 'output'):
        p.add_argument('--'+key, type=Path)
    p.add_argument('--amendment-sha256'); p.add_argument('--inputs-sha256'); p.add_argument('--expected-source')
    args = p.parse_args()
    if not args.execute:
        print(json.dumps(dict(assigned_screen_attempts=8, max_model_calls_per_chunk=4, retries=0, paid_calls=0, live_execution=False)))
        return
    if any(v is None for k,v in vars(args).items() if k not in ('execute','prior')):
        p.error('explicit immutable inputs/source, existing receipt/audit/tokenizer and fresh output required')
    if subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'], text=True).strip() != args.expected_source:
        raise ValueError('source commit differs')
    subprocess.run(['git','-C',str(ROOT),'diff','--quiet','HEAD'], check=True)
    from zoneinfo import ZoneInfo
    local = datetime.now(ZoneInfo('America/Toronto'))
    stop = local.replace(hour=23, minute=0, second=0, microsecond=0)
    seconds = min(1200, (stop-local).total_seconds())
    if seconds <= 0 or args.output.exists():
        raise ValueError('operating window and fresh archive required')
    os.umask(0o077)
    sys.path.insert(0, str(ROOT/'integrations/software-repair/scripts'))
    from screen_deadline import run_bounded
    result = run_bounded(execute, (args,), seconds, args.output.with_suffix('.supervision.jsonl'))
    print(json.dumps(result))


if __name__ == '__main__': main()
