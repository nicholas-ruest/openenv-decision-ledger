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
from failure_diagnostics import safe_failure

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def modules():
    sys.path[:0] = [str(ROOT / p) for p in (
        'research/software-function-block-protocol-20261028',
        'research/software-function-trial-20261029')]
    import protocol
    from trial import Trial
    return protocol, Trial


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked_inputs(bundle, expected):
    protocol, _ = modules()
    if protocol.digest(bundle) != expected:
        raise ValueError('immutable inputs differ')
    for phase in ('screen', 'confirmation'):
        if bundle[phase+'_jobs'] != protocol.schedule(phase, bundle['namespace']):
            raise ValueError('frozen complete assignment schedule required')
    if (bundle['confirmation_observations_materialized'] is not False or
            bundle['sampling'] != protocol.SAMPLING or
            bundle['max_model_calls_per_attempt'] != 1 or
            bundle['max_model_calls_per_phase'] != 32 or bundle['max_retries'] != 0 or
            bundle['completion_tokens_including_postreset_observations'] != 4096 or
            bundle['context_tokens'] != 8192):
        raise ValueError('frozen screen contract required')
    groups = bundle['screen_groups']
    if len(groups) != 4:
        raise ValueError('four paired task/seed groups required')
    for group in groups:
        for arm in protocol.ARMS:
            actual = protocol.capture(group['task_id'], group['seed'], arm)
            if actual != group['arms'][arm] or actual['problem_sha256'] != group['problem_sha256']:
                raise ValueError('native problem/request differs from frozen input')
    return bundle['screen_jobs']


def record(stream, value):
    stream.write(json.dumps(value, allow_nan=False) + '\n')
    stream.flush()
    os.fsync(stream.fileno())


def phase(bundle, expected, output, backend, counter, deadline):
    """Backend may be the guarded live adapter or an explicitly scripted test.

    Normal completion retains all assigned outcomes. A killed worker leaves an
    incomplete durable archive, never a completed result or automatic restart.
    """
    protocol, Trial = modules()
    jobs = checked_inputs(bundle, expected)
    if output.exists():
        raise ValueError('fresh output directory required; no resume/redraw')
    requests = {}
    for group in bundle['screen_groups']:
        for arm, value in group['arms'].items():
            requests[group['task_id'], group['seed'], arm] = value
    # The quote covers every assigned call; no shrinking the phase to fit.
    bounds = [len(protocol.canonical(requests[j['task_id'], j['seed'], j['arm']]['messages']).encode())+4096 for j in jobs]
    backend.admit(bounds, 2048, deadline)
    output.mkdir(mode=0o700)
    result = []
    stopped = False
    responses = set()
    with (output/'events.jsonl').open('x') as events, (output/'records.jsonl').open('x') as records:
        for job, bound in zip(jobs, bounds):
            frozen = requests[job['task_id'], job['seed'], job['arm']]
            row = dict(job, prompt_sha256=frozen['prompt_sha256'], problem_sha256=frozen['problem_sha256'],
                       call_id=None, response_id=None, reservation_label=None,
                       generation_tokens=0, observation_tokens=0, finish_reason=None,
                       terminal_reward_observed=None, semantic_reward=None, category='budget')
            if stopped or time.monotonic() >= deadline:
                stopped = True
                record(records, row); result.append(row); continue
            trial = Trial(job, frozen['prompt_sha256'], frozen['problem_sha256'])
            if trial.messages != frozen['messages']:
                raise ValueError('native trial messages changed')
            if counter.context(trial.messages)+2048 > 8192:
                record(records, row); result.append(row); continue
            label = job['attempt_id']+':0'
            record(events, dict(event='intent', attempt_id=job['attempt_id'], label=label))
            diagnostic_started = time.monotonic()
            try:
                backend.reserve(label, bound, 2048, deadline)
            except Exception as exc:
                record(events, dict(event='failure', attempt_id=job['attempt_id'], **safe_failure(exc, 'reservation', time.monotonic()-diagnostic_started)))
                stopped = True
                record(records, row); result.append(row); continue
            row.update(reservation_label=label)
            record(events, dict(event='reserved', attempt_id=job['attempt_id'], label=label))
            diagnostic_started = time.monotonic()
            diagnostic_stage = 'provider'
            try:
                if time.monotonic() >= deadline:
                    raise TimeoutError('local deadline')
                row.update(call_id=label, generation_tokens=None, category='provider')
                record(events, dict(event='calling', attempt_id=job['attempt_id'], call_id=label))
                response = backend.call(copy.deepcopy(frozen['request']), min(180, deadline-time.monotonic()), job)
                diagnostic_stage = 'response_validation'
                # Entire reply is credential-checked before any raw data is saved.
                backend.check_reply(response)
                identity = response.get('id')
                if not isinstance(identity, str) or not identity:
                    raise ValueError('missing response identity')
                response_id = hashlib.sha256(identity.encode()).hexdigest()
                if response_id in responses:
                    stopped = True
                    raise ValueError('reused response identity')
                responses.add(response_id); row['response_id'] = response_id
                record(events, dict(event='response', attempt_id=job['attempt_id'], response=response))
                usage = response.get('usage', {})
                for key in ('prompt_tokens', 'completion_tokens'):
                    if type(usage.get(key)) is not int or usage[key] < 0:
                        raise ValueError('unverified usage')
                row['generation_tokens'] = usage['completion_tokens']
                if usage['prompt_tokens'] > bound or usage['completion_tokens'] > 2048:
                    stopped = True; row['category'] = 'budget'
                    raise ValueError('usage exceeds reservation')
                choices = response['choices']
                if not isinstance(choices, list) or len(choices) != 1:
                    raise ValueError('one response choice required')
                choice = choices[0]; message = choice['message']
                row['finish_reason'] = choice.get('finish_reason')
                backend.check_message(message)
                diagnostic_stage = 'native_processing'
                value = trial.consume(message.get('content'), finish_reason=row['finish_reason'])
                row.update(category=value['category'], semantic_reward=value['semantic_reward'],
                           terminal_reward_observed=value['native_reward'])
                if trial.native is not None:
                    terminal = protocol.canonical(trial.native)
                    row['observation_tokens'] = counter.count(terminal)
                    accounted = frozen['messages']+[message, dict(role='user', content=terminal)]
                    context = max(counter.context(accounted), usage['prompt_tokens']+usage['completion_tokens']+row['observation_tokens'])
                    if usage['completion_tokens']+row['observation_tokens'] > 4096 or context > 8192:
                        row.update(category='budget', semantic_reward=None)
            except Exception as exc:
                record(events, dict(event='failure', attempt_id=job['attempt_id'], **safe_failure(exc, diagnostic_stage, time.monotonic()-diagnostic_started)))
                # Do not log exception text (may contain credential/provider text).
                # Unknown usage stays null and never becomes a free completion.
                if row['generation_tokens'] is None:
                    stopped = True
            record(records, row); result.append(row)
    summary = dict(assigned_attempts=32, recorded_attempts=len(result),
                   observed_calls=sum(r['call_id'] is not None for r in result),
                   fresh_model_confirmation=False, model_improvement=False, is_training=False,
                   arena_wrapper_equivalent=False, thinking_verified=False,
                   source_inputs_sha256=expected, scripted=backend.scripted)
    (output/'complete.json').write_text(json.dumps(summary, indent=2)+'\n')
    return result


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
        self.budget = self.base.DollarReservations(receipt, amendment_sha256=amendment_sha256)
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
        quote = module.admit(32, bounds, generation, self.frozen['provider']['pricing'], min(remaining, self.credit))
        if not quote['admitted'] or time.monotonic() >= deadline:
            raise ValueError('complete phase cannot fit existing allocation/deadline')
    def reserve(self, label, prompt, generation, deadline):
        timeout = self.base.request_timeout(deadline, 15)
        if self.base.quote(self.opener, self.token, timeout) != self.frozen:
            raise ValueError('selected route metadata changed')
        self.base.request_timeout(deadline, 180)
        return self.budget.reserve(label, prompt, generation, self.frozen['provider']['pricing'])
    def call(self, payload, timeout, job):
        return self.base.helper.provider_call(self.opener, self.base.BASE, self.token, payload, timeout)
    def check_reply(self, response):
        if self.token in json.dumps(response, allow_nan=False):
            raise ValueError('credential leakage guard')
    def check_message(self, message):
        _, _, _, _, error, leaked = self.base.helper.reasoning_payload(message, self.token)
        if error or leaked or message.get('tool_calls') or message.get('function_call'):
            raise ValueError('invalid provider message')


def execute(deadline, args):
    backend = LiveBackend(args.receipt, args.reconciliation, args.tokenizer, args.amendment_sha256)
    bundle = json.loads(args.inputs.read_text())
    phase(bundle, args.inputs_sha256, args.output, backend, backend.counter, deadline)
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute', action='store_true')
    for key in ('inputs', 'receipt', 'reconciliation', 'tokenizer', 'output'):
        p.add_argument('--'+key, type=Path)
    p.add_argument('--amendment-sha256'); p.add_argument('--inputs-sha256'); p.add_argument('--expected-source')
    args = p.parse_args()
    if not args.execute:
        print(json.dumps(dict(assigned_screen_attempts=32, max_model_calls=32, retries=0, paid_calls=0, live_execution=False)))
        return
    if any(v is None for k,v in vars(args).items() if k != 'execute'):
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
