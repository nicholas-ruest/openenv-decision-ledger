"""Four-call completion-budget feasibility screen; no promotion/submission authority."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from decimal import Decimal

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/p) for p in ('research/software-function-caller-20261029',
    'research/software-function-block-protocol-20261028','research/software-terminal-audit-20261028',
    'integrations/software-repair','scripts')]
from caller import LiveBackend,record,load
from failure_diagnostics import safe_failure
import protocol
from repair_env.direct_environment import DirectRepairEnvironment,DirectRepairAction
from terminal_audit import classify
from types import SimpleNamespace


def plan():
    jobs=[]
    # Two fresh cases, one response per limit/case. Alternate order; no
    # helper-preservation arm, response revision, retry or confirmation.
    for index,(task,seed) in enumerate((('software_repair-ignore-d3',2490000),
                                       ('software_repair-ignore-d4',2490100))):
        frozen=protocol.capture(task,seed,'full_module')
        for limit in ((2048,4000) if index==0 else (4000,2048)):
            request=copy.deepcopy(frozen['request']);request['max_tokens']=limit
            job=dict(task_id=task,seed=seed,max_tokens=limit,prompt_sha256=frozen['prompt_sha256'],
                     problem_sha256=frozen['problem_sha256'],request=request)
            job['attempt_id']=protocol.digest(job);jobs.append(job)
    return dict(purpose='completion-budget feasibility only',jobs=jobs,max_calls=4,retries=0,
                completion_with_observations=4096,context=8192,reserved_terminal_tokens=96,
                model_comparison_of_helpers=False,confirmation=False,promotion=False,
                analysis='Retain four assigned outcomes. Report truncation/format/provider/budget/execution separately from full/partial/wrong. Two cases and one draw per cell cannot establish causal gain or transfer.')


def execute(deadline,args):
    value=json.loads(args.inputs.read_text())
    if value!=plan() or protocol.digest(value)!=args.inputs_sha256:
        raise ValueError('frozen four-call feasibility plan changed')
    backend=LiveBackend(args.receipt,args.audit,args.tokenizer,args.amendment_sha256)
    jobs=value['jobs'];bounds=[len(protocol.canonical(j['request']['messages']).encode())+4096 for j in jobs]
    module=load('feasibility_admission',ROOT/'scripts/stage-phase-admission.py')
    quotes=[Decimal(module.admit(1,[bound],j['max_tokens'],backend.frozen['provider']['pricing'],backend.credit)['quoted_usd']) for j,bound in zip(jobs,bounds)]
    used=sum((Decimal(json.loads(x)['usd']) for x in backend.budget.ledger.read_text().splitlines() if x),Decimal(0))
    if sum(quotes)>min(backend.credit,backend.budget.cap-used):raise ValueError('whole phase not admitted')
    args.output.mkdir(mode=0o700);stopped=False;rows=[]
    with (args.output/'events.jsonl').open('x') as events,(args.output/'records.jsonl').open('x') as output:
        for job,bound in zip(jobs,bounds):
            row={k:v for k,v in job.items() if k!='request'}
            row.update(category='budget',native_reward=None,generation_tokens=0,observation_tokens=0,finish_reason=None,call_id=None)
            if stopped or time.monotonic()>=deadline:
                stopped=True;record(output,row);rows.append(row);continue
            env=DirectRepairEnvironment();reset=env.reset(task_id=job['task_id'],seed=job['seed']).model_dump()
            if reset!=json.loads(job['request']['messages'][1]['content']):raise ValueError('native reset changed')
            if backend.counter.context(job['request']['messages'])+job['max_tokens']+96>8192:
                stopped=True;record(output,row);rows.append(row);continue
            stage='reservation';started=time.monotonic()
            try:
                label='budget-feasibility-20261029-'+job['attempt_id']
                record(events,dict(event='intent',attempt_id=job['attempt_id']))
                backend.reserve(label,bound,job['max_tokens'],deadline)
                row.update(call_id=label,category='provider',generation_tokens=None)
                record(events,dict(event='calling',attempt_id=job['attempt_id']))
                stage='provider';reply=backend.call(job['request'],min(180,deadline-time.monotonic()),job)
                stage='response_validation';backend.check_reply(reply)
                record(events,dict(event='response',attempt_id=job['attempt_id'],response=reply))
                usage=reply['usage']
                if not all(type(usage.get(k)) is int and usage[k]>=0 for k in ('prompt_tokens','completion_tokens')):raise ValueError('unknown usage')
                row['generation_tokens']=usage['completion_tokens']
                if usage['prompt_tokens']>bound or usage['completion_tokens']>job['max_tokens']:
                    row['category']='budget';stopped=True;raise ValueError('reservation exceeded')
                choice=reply['choices']
                if len(choice)!=1:raise ValueError('one choice required')
                choice=choice[0];row['finish_reason']=choice.get('finish_reason');message=choice['message'];backend.check_message(message)
                if row['finish_reason']=='length':row['category']='truncation'
                elif row['finish_reason']!='stop':row['category']='provider'
                else:
                    stage='native_processing'
                    try:action=DirectRepairAction.model_validate_json(message.get('content'),strict=True)
                    except (ValueError,TypeError):row['category']='format'
                    else:
                        native=env.step(action).model_dump();diagnosis=classify(SimpleNamespace(_direct=env),native)
                        row.update(category=diagnosis['category'],native_reward=diagnosis['native_reward'])
                        terminal=protocol.canonical(native);row['observation_tokens']=backend.counter.count(terminal)
                        messages=job['request']['messages']+[message,dict(role='user',content=terminal)]
                        context=max(backend.counter.context(messages),usage['prompt_tokens']+usage['completion_tokens']+row['observation_tokens'])
                        if usage['completion_tokens']+row['observation_tokens']>4096 or context>8192:
                            row.update(category='budget',native_reward=None)
            except Exception as exc:
                record(events,dict(event='failure',attempt_id=job['attempt_id'],**safe_failure(exc,stage,time.monotonic()-started)))
                if row['generation_tokens'] is None:stopped=True
                elif stage=='native_processing':row['category']='execution'
            record(output,row);rows.append(row)
    summary=dict(assigned=4,recorded=len(rows),observed_calls=sum(r['call_id'] is not None for r in rows),
                 model_improvement=False,leaderboard_gain=False,confirmation=False,promotion=False)
    (args.output/'complete.json').write_text(json.dumps(summary,indent=2)+'\n');return 0


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',type=Path)
    for field in ('receipt','audit','tokenizer','inputs','output'):p.add_argument('--'+field,type=Path)
    for field in ('inputs-sha256','amendment-sha256','expected-source'):p.add_argument('--'+field)
    args=p.parse_args()
    if args.prepare:
        with args.prepare.open('x') as f:json.dump(plan(),f,indent=2)
        print(protocol.digest(plan()))
    else:
        if any(v is None for k,v in vars(args).items() if k!='prepare'):p.error('explicit frozen plan/accounting/source required')
        if subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()!=args.expected_source:raise ValueError('source differs')
        subprocess.run(['git','-C',str(ROOT),'diff','--quiet','HEAD'],check=True)
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from screen_deadline import run_bounded
        now=datetime.now(ZoneInfo('America/Toronto'));seconds=min(1200,(now.replace(hour=23,minute=0,second=0,microsecond=0)-now).total_seconds())
        if seconds<=0 or args.output.exists():raise ValueError('fresh archive and operating window required')
        os.umask(0o077);print(json.dumps(run_bounded(execute,(args,),seconds,args.output.with_suffix('.supervision.jsonl'))))
