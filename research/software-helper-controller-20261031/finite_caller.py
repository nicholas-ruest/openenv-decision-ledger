"""Finite helper-controller orchestration. Live admission is deliberately sealed.

Backends must reserve before every call and never release unknown usage. This
module has no credential loading, provider transport or budget mutation API.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import time

import matched_protocol as protocol

LIVE_CASE_AUDIT_SHA256 = None


def require_live_ready():
    # Explicitly source-bound, not an environment/CLI permission or broad bypass.
    if LIVE_CASE_AUDIT_SHA256 is None:
        raise ValueError('unsealed live source/case admission; backend construction refused')
    # Production materialization is independently blocked in this source too.
    protocol.materialize(protocol.jobs('screen')[0])


def write(path, value):
    with path.open('a') as f:
        f.write(protocol.canonical(value)+'\n'); f.flush(); os.fsync(f.fileno())


def qualification_chunk(chunk, backend, counter, output, deadline):
    """Run two exact original assignments. Scripted qualification backend only."""
    if type(chunk) is not int or chunk not in range(4) or backend.scripted is not True:
        raise ValueError('qualification backend and original chunk required')
    assigned = [j for j in protocol.jobs('qualification') if j['sample']==chunk]
    if output.exists() or deadline <= time.monotonic():
        raise ValueError('fresh archive and unexpired phase deadline required')
    output.mkdir(parents=True)
    events=output/'events.jsonl'; records=output/'records.jsonl'; rows=[]
    stopped=False
    for job in assigned:
        if stopped:break
        start=time.monotonic(); attempt_deadline=min(deadline,start+600)
        trace=dict(job=copy.deepcopy(job),scripted=True,events=[])
        row=dict(job=copy.deepcopy(job),category='budget',generation_tokens=0,
            native_observation_tokens=0,controller_observation_tokens=0,
            reservations=[],calls=[],response_ids=[],unknown_usage=False)
        try:
            trial=protocol.QualificationTrial(job)
        except Exception as exc:
            row['category']='execution';stopped=True
            write(events,dict(event='failure',attempt_id=job['attempt_id'],stage='native_initialization',error_type=type(exc).__name__,unknown_usage=False))
            write(records,row);rows.append(row);break
        for turn in range(2):
            spent=row['generation_tokens']+row['native_observation_tokens']+row['controller_observation_tokens']
            limit=6000 if turn==0 else 8192-spent-96
            remaining=attempt_deadline-time.monotonic()
            if limit <= 0 or remaining <= 0 or counter.context(trial.messages)+limit>24576:
                stopped=True;break
            messages=trial.messages
            payload=dict(protocol.SAMPLING,messages=messages,max_tokens=limit)
            label=job['attempt_id']+':'+str(turn)
            called=False;known=False;stage='reservation'
            try:
                backend.reserve(label,28672,limit,attempt_deadline)
                row['reservations'].append(label)
                write(events,dict(event='reserved',attempt_id=job['attempt_id'],turn=turn,label=label))
                if time.monotonic()>=attempt_deadline:
                    row['category']='budget';stopped=True;break
                stage='provider';called=True;row['calls'].append(label)
                write(events,dict(event='calling',attempt_id=job['attempt_id'],turn=turn,label=label))
                response=backend.call(payload,min(360,attempt_deadline-time.monotonic()),job)
                stage='response_validation'
                usage=response.get('usage',{});choices=response.get('choices')
                identity=response.get('id')
                if (not isinstance(identity,str) or not identity or identity in [x for r in rows for x in r['response_ids']]+row['response_ids']
                        or any(type(usage.get(k)) is not int or usage[k]<0 for k in ('prompt_tokens','completion_tokens'))
                        or not isinstance(choices,list) or len(choices)!=1):
                    raise ValueError('unique reply and complete verified usage required')
                backend.check_reply(response)
                known=True;row['response_ids'].append(identity)
                row['generation_tokens']+=usage['completion_tokens']
                write(events,dict(event='response',attempt_id=job['attempt_id'],turn=turn,response=response))
                if (time.monotonic()>attempt_deadline or usage['completion_tokens']>limit
                        or usage['prompt_tokens']>28672 or usage['prompt_tokens']+usage['completion_tokens']>24576):
                    row['category']='budget';stopped=True;break
                e=dict(response=response,prompt_sha256=protocol.digest(messages),requested_max_tokens=limit)
                choice=choices[0];finish=choice.get('finish_reason')
                if finish=='length':
                    e.update(native_observations=[],controller_observations=[],controller_actions=copy.deepcopy(trial.policy.controller_actions))
                    trace['events'].append(e);row['category']='truncation';break
                if finish!='stop':
                    row['category']='provider';stopped=True;break
                backend.check_message(choice['message'])
                stage='native_processing';value=trial.consume(choice['message'].get('content'))
                e.update(native_observations=value['new_observations'],controller_observations=value['controller_observations'],controller_actions=value['controller_actions'])
                trace['events'].append(e)
                row['native_observation_tokens']+=sum(counter.count(protocol.canonical(x)) for x in value['new_observations'])
                row['controller_observation_tokens']+=sum(counter.count(protocol.canonical(x)) for x in value['controller_observations'])
                row['category']=value['category']
                if (time.monotonic()>attempt_deadline
                        or row['generation_tokens']+row['native_observation_tokens']+row['controller_observation_tokens']>8192
                        or counter.context(trial.messages)>24576):
                    row['category']='budget';stopped=True;break
                if value['done']:break
            except Exception as exc:
                # No refund API exists here. A called-but-unverified turn retains
                # its full reservation even when earlier replies had known usage.
                row['unknown_usage']=called and not known
                row['category']='budget' if stage=='reservation' else 'execution' if stage=='native_processing' else 'provider'
                if row['unknown_usage']:row['generation_tokens']=None
                write(events,dict(event='failure',attempt_id=job['attempt_id'],turn=turn,stage=stage,error_type=type(exc).__name__,unknown_usage=row['unknown_usage']))
                stopped=True;break
        if row['category']=='awaiting_revision':row['category']='budget';stopped=True
        row['controller_actions']=copy.deepcopy(trial.policy.controller_actions)
        write(records,row);rows.append(row)
        if not stopped:
            trace['record']=dict(category=row['category'],generation_tokens=row['generation_tokens'],
                native_observation_tokens=row['native_observation_tokens'],controller_observation_tokens=row['controller_observation_tokens'],
                completion_with_observations=row['generation_tokens']+row['native_observation_tokens']+row['controller_observation_tokens'],
                model_responses=len(trace['events']),controller_actions=row['controller_actions'],
                model_response_only_full=row['category']=='full' and not row['controller_actions'],
                controller_assisted_full=row['category']=='full' and bool(row['controller_actions']))
            (output/(job['attempt_id']+'.trace.json')).write_text(json.dumps(trace,indent=2)+'\n')
    summary=dict(scripted=True,live_evidence=False,assigned_attempts=2,recorded_attempts=len(rows),
        observed_calls=sum(len(r['calls']) for r in rows),stopped_on_failure=stopped,
        unknown_usage_calls=sum(r['unknown_usage'] for r in rows),uncalled_assignments=2-len(rows),retries=0)
    (output/'complete.json').write_text(json.dumps(summary,indent=2)+'\n')
    return rows,summary


def main():
    parser=argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if args.execute:require_live_ready()
    print(json.dumps(dict(paid_execution_ready=False,qualification_only=True,provider_calls=0)))


if __name__=='__main__':main()
