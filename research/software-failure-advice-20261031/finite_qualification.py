"""Bounded reserve-before-call qualification and source-sealed screen orchestration."""
import copy
import json
import os
from pathlib import Path
import time
import failure_protocol as p


def require_live_ready(case_audit=None,case_sha256=None):
    from failure_materializer import verify_case
    return verify_case(p.jobs('screen')[0],case_audit,case_sha256)


def write(path,value):
    with path.open('a') as f:f.write(p.canonical(value)+'\n');f.flush();os.fsync(f.fileno())


def run_chunk(chunk,backend,counter,output,deadline):
    if type(chunk) is not int or chunk not in range(4) or backend.scripted is not True:
        raise ValueError('original scripted qualification chunk required')
    return _run_chunk(chunk,backend,counter,output,deadline,p.jobs('qualification'),p.QualificationTrial,True,{})


def run_screen_chunk(chunk,backend,counter,output,deadline,case_audit,case_sha256):
    proof=require_live_ready(case_audit,case_sha256)
    if type(chunk) is not int or chunk not in range(4) or backend.scripted is not False:
        raise ValueError('original screen chunk and financial backend required')
    if Path(output).exists():raise ValueError('fresh archive required before financial admission')
    backend.admit([28672]*16,8096,deadline)
    from failure_materializer import execution_hashes
    metadata=dict(case_audit_sha256=proof['case_audit_sha256'],execution_sha256=execution_hashes())
    return _run_chunk(chunk,backend,counter,output,deadline,p.jobs('screen'),
        lambda job:p.materialize(job,case_audit,case_sha256),False,metadata)


def _run_chunk(chunk,backend,counter,output,deadline,assignments,factory,scripted,metadata):
    output=Path(output)
    if output.exists() or deadline<=time.monotonic():raise ValueError('fresh archive and phase deadline required')
    output.mkdir(mode=0o700,parents=True);events=output/'events.jsonl';records=output/'records.jsonl'
    jobs=[j for j in assignments if j['sample']==chunk];rows=[];stopped=False
    for job in jobs:
        if stopped:break
        attempt=min(deadline,time.monotonic()+600)
        row=dict(job=copy.deepcopy(job),category='budget',generation_tokens=0,native_observation_tokens=0,
            advice_observation_tokens=0,advice_deliveries=0,reservations=[],calls=[],response_ids=[],unknown_usage=False)
        trace=dict(job=copy.deepcopy(job),scripted=scripted,live_evidence=not scripted,events=[])
        if not scripted:trace.update(metadata,requests=[])
        try:trial=factory(job)
        except Exception as exc:
            row['category']='execution';stopped=True
            write(events,dict(event='failure',attempt_id=job['attempt_id'],stage='native_initialization',error_type=type(exc).__name__,unknown_usage=False))
            write(records,row);rows.append(row);break
        for turn in range(2):
            known=False;called=False;stage='accounting'
            try:
                limit=6000 if turn==0 else 8192-row['generation_tokens']-row['native_observation_tokens']-row['advice_observation_tokens']-96
                if limit<=0 or time.monotonic()>=attempt or counter.context(trial.messages)+limit+96>24576:
                    row['category']='budget';stopped=True;break
                messages=trial.messages;payload=dict(p.sampling_for(job,turn),messages=messages,max_tokens=limit)
                label=job['attempt_id']+':'+str(turn);stage='reservation'
                backend.reserve(label,28672,limit,attempt);row['reservations'].append(label)
                write(events,dict(event='reserved',attempt_id=job['attempt_id'],turn=turn,label=label))
                if time.monotonic()>=attempt:row['category']='budget';stopped=True;break
                stage='provider';called=True;row['calls'].append(label)
                request=dict(request_sha256=p.digest(payload),prompt_sha256=p.digest(messages),requested_max_tokens=limit)
                write(events,dict(event='calling',attempt_id=job['attempt_id'],turn=turn,label=label,**request))
                if not scripted:trace['requests'].append(request)
                response=backend.call(payload,min(360,attempt-time.monotonic()),job)
                stage='response_validation';backend.check_reply(response)
                usage=response.get('usage',{});identity=response.get('id');choices=response.get('choices')
                if (not isinstance(identity,str) or not identity or identity in [i for r in rows for i in r['response_ids']]+row['response_ids']
                    or any(type(usage.get(k)) is not int or usage[k]<0 for k in ('prompt_tokens','completion_tokens'))
                    or not isinstance(choices,list) or len(choices)!=1):raise ValueError('unique reply and verified usage required')
                known=True;row['response_ids'].append(identity);prior_generation=row['generation_tokens'];row['generation_tokens']+=usage['completion_tokens']
                write(events,dict(event='response',attempt_id=job['attempt_id'],turn=turn,response=response))
                if (time.monotonic()>=attempt or usage['completion_tokens']>limit or usage['prompt_tokens']>28672
                        or usage['prompt_tokens']+usage['completion_tokens']>24576):
                    row['category']='budget';stopped=True;break
                backend.check_message(choices[0]['message'])
                if choices[0].get('finish_reason') not in ('stop','length'):
                    row['category']='provider';stopped=True;break
                stage='native_processing'
                e,g,n,a,category,done,reward,terminal_reward=p._process(trial,response,turn,counter,prior_generation,row['native_observation_tokens'],row['advice_observation_tokens'])
                trace['events'].append(e)
                row.update(category=category,generation_tokens=g,native_observation_tokens=n,advice_observation_tokens=a,
                    advice_deliveries=row['advice_deliveries']+int(e['advice_delivered']))
                if time.monotonic()>=attempt:row['category']='budget';stopped=True;break
                if done:break
            except Exception as exc:
                row['unknown_usage']=called and not known
                if row['unknown_usage']:row['generation_tokens']=None
                row['category']=('budget' if stage=='reservation' or isinstance(exc,p.ObservationBudgetExceeded)
                    else 'provider' if stage in ('provider','response_validation') else 'execution')
                write(events,dict(event='failure',attempt_id=job['attempt_id'],turn=turn,stage=stage,error_type=type(exc).__name__,unknown_usage=row['unknown_usage']))
                stopped=True;break
        if row['category']=='awaiting_revision':row['category']='budget';stopped=True
        write(records,row);rows.append(row)
        if not stopped:
            trace['record']=dict(category=row['category'],generation_tokens=row['generation_tokens'],native_observation_tokens=row['native_observation_tokens'],
                advice_observation_tokens=row['advice_observation_tokens'],completion_with_observations=row['generation_tokens']+row['native_observation_tokens']+row['advice_observation_tokens'],
                model_responses=len(trace['events']),advice_deliveries=row['advice_deliveries'],semantic_reward=reward,
                terminal_reward_observed=terminal_reward,finish_reason=trace['events'][-1]['response']['choices'][0]['finish_reason'])
            with (output/(job['attempt_id']+'.trace.json')).open('x') as f:json.dump(trace,f,indent=2)
    summary=dict(scripted=scripted,live_evidence=not scripted,assigned_attempts=2,recorded_attempts=len(rows),uncalled_assignments=2-len(rows),
        observed_calls=sum(len(r['calls']) for r in rows),unknown_usage_calls=sum(r['unknown_usage'] for r in rows),stopped_on_failure=stopped,retries=0)
    summary.update(metadata)
    with (output/'complete.json').open('x') as f:json.dump(summary,f,indent=2)
    return rows,summary


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(allow_abbrev=False);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    if args.execute:require_live_ready()
    print(json.dumps(p.plan()))
