"""Qualification-only two-slot paired caller; no live materializer or provider."""
from concurrent.futures import ThreadPoolExecutor
import json
import math
import os
from pathlib import Path
import threading
import time
import matched_note as p


def plan():
    value=p.plan()
    value.update(live_continuation_policy_frozen=True,max_inflight_requests=2,
        scheduling='four sequential counterbalanced pairs, at most two original requests in flight, one supervised process',
        failure_policy='Retain independently replayed model-program rejection/runtime errors at Native reward zero and no semantic credit; retain format/truncation outcomes. Stop new pairs on provider, budget, unknown-usage or unverified Native execution failure; preserve already reserved/in-flight attempts.',
        selection='Complete all eight original assignments with known usage and independent replay; positive full-repair difference and nonnegative all-assignment semantic mean difference; no provider/budget/unverified Native failure. Require unchanged fresh disjoint confirmation before any improvement claim.',
        live_execution_ready=False,live_source_case_materializer_unsealed=True)
    return value


def stops_phase(record):
    """New protocol policy only. Never relabel/reopen the closed helper study."""
    category=record['category'];origin=record['failure_origin']
    if category=='execution':
        if (origin=='model_program_rejection' and record['native_compile_rejected'] is True
            and record['terminal_reward_observed']==0 and record['semantic_reward'] is None):return False
        if (origin=='model_program_runtime_error' and record['native_runtime_error_observed'] is True
            and record['native_compile_rejected'] is False
            and record['terminal_reward_observed']==0 and record['semantic_reward'] is None):return False
        return True
    if category in ('provider','budget'):return True
    if category in ('format','truncation'):return origin!='model_output_'+category
    if category in ('full','partial','wrong'):
        semantic=record['semantic_reward'];reward=record['terminal_reward_observed']
        return not (origin=='native_semantic_outcome' and semantic==reward and
                    (semantic==1 if category=='full' else semantic==0 if category=='wrong' else 0<semantic<1))
    raise ValueError('unknown independently verified outcome')


def write(path,value):
    with path.open('x') as stream:
        json.dump(value,stream,sort_keys=True,indent=2);stream.flush();os.fsync(stream.fileno())


def event(path,value):
    value=dict(value,observed_monotonic=time.monotonic())
    with path.open('a') as stream:
        stream.write(p.n.original.canonical(value)+'\n');stream.flush();os.fsync(stream.fileno())


def attempt(job,backend,counter,path,deadline,stop,seen,seen_lock):
    path.mkdir(mode=0o700);events=path/'events.jsonl'
    row=dict(job=job,category='budget',failure_origin='budget_failure',reservations=[],calls=[],
             response_ids=[],unknown_usage=False,generation_tokens=0)
    attempt_deadline=min(deadline,time.monotonic()+600)
    stage='native_initialization';called=known=False
    try:
        trial=p.n.QualificationTrial(p.n.job(job['arm']))
        payload=dict(p.n.original.SAMPLING,messages=trial.messages,max_tokens=6000)
        if stop.is_set() or time.monotonic()>=attempt_deadline or counter.context(trial.messages)+6096>24576:
            stop.set()
        else:
            label=job['attempt_id']+':0';stage='reservation'
            backend.reserve(label,28672,6000,attempt_deadline);row['reservations'].append(label)
            event(events,dict(event='reserved',label=label))
            if stop.is_set() or time.monotonic()>=attempt_deadline:
                stop.set() # Any uncalled reservation stays retained.
            else:
                write(path/'request.json',payload)
                stage='provider';called=True;row['calls'].append(label)
                event(events,dict(event='calling',label=label,request_sha256=p.n.original.digest(payload),requested_max_tokens=6000))
                response=backend.call(payload,min(360,attempt_deadline-time.monotonic()),job)
                stage='response_validation';backend.check_reply(response)
                usage=response.get('usage',{});identity=response.get('id');choices=response.get('choices')
                if (not isinstance(identity,str) or not identity
                    or any(type(usage.get(k)) is not int or usage[k]<0 for k in ('prompt_tokens','completion_tokens'))
                    or not isinstance(choices,list) or len(choices)!=1):raise ValueError('known original response/usage required')
                with seen_lock:
                    if identity in seen:raise ValueError('cross-attempt response reuse')
                    seen.add(identity)
                known=True;row['response_ids'].append(identity);row['generation_tokens']=usage['completion_tokens']
                write(path/'response.json',response);event(events,dict(event='response_received',response_id=identity))
                backend.check_message(choices[0]['message']);stage='accounting'
                if (usage['completion_tokens']>6000 or usage['prompt_tokens']>28672
                    or usage['prompt_tokens']+usage['completion_tokens']>24576):raise ValueError('actual token/context overrun')
                if time.monotonic()>=attempt_deadline:stop.set()
                else:
                    stage='native_replay';trace=p.observe(job,response,counter);verified=p.verify(trace,counter)
                    if trace['request_sha256']!=p.n.original.digest(payload):raise ValueError('original request changed')
                    row.update(verified)
                    if time.monotonic()>=attempt_deadline:
                        row.update(category='budget',failure_origin='budget_failure');stop.set()
                    else:
                        write(path/'trace.json',trace)
                        if stops_phase(verified):stop.set()
    except Exception as exc:
        row['unknown_usage']=called and not known
        if row['unknown_usage']:row['generation_tokens']=None
        category='budget' if stage in ('reservation','accounting') else 'provider' if stage in ('provider','response_validation') else 'execution'
        row.update(category=category,failure_origin=category+'_failure' if category!='execution' else 'native_execution_unverified')
        event(events,dict(event='failure',stage=stage,error_type=type(exc).__name__,unknown_usage=row['unknown_usage']))
        stop.set()
    write(path/'record.json',row)
    return row


def run(backend,counter,output,deadline):
    if backend.scripted is not True:raise ValueError('qualification only; live execution unsealed')
    output=Path(output)
    if (output.exists() or type(deadline) not in (int,float) or not math.isfinite(deadline)
        or not 0<deadline-time.monotonic()<=1200):raise ValueError('fresh archive and original deadline required')
    backend.admit([28672]*8,6000,deadline)
    output.mkdir(mode=0o700,parents=True)
    assigned=p.jobs('qualification');write(output/'assignments.json',assigned)
    stop=threading.Event();seen=set();seen_lock=threading.Lock();rows=[]
    # Four sequential pairs, at most two in-flight requests, one supervised
    # process. This launches no agents, services, timers or duplicate studies.
    with ThreadPoolExecutor(max_workers=2) as pool:
        for pair in range(4):
            if stop.is_set() or time.monotonic()>=deadline:break
            current=assigned[2*pair:2*pair+2]
            futures=[pool.submit(attempt,j,backend,counter,output/j['attempt_id'],deadline,stop,seen,seen_lock) for j in current]
            rows.extend(f.result() for f in futures)
    report=assemble(output,counter)
    if time.monotonic()>=deadline:stop.set()
    summary=dict(scripted=True,live_evidence=False,assigned=8,recorded=len(rows),complete=report['complete'],
        calls=sum(len(r['calls']) for r in rows),unknown_usage_calls=sum(r['unknown_usage'] for r in rows),
        max_inflight_requests=2,stopped_on_infrastructure_or_budget=stop.is_set(),retries=0,selection_passed=False)
    summary['complete']=summary['complete'] and not stop.is_set()
    write(output/'complete.json',summary)
    return rows,summary


def assemble(output,counter):
    output=Path(output);assigned=p.jobs('qualification')
    if json.loads((output/'assignments.json').read_text())!=assigned:raise ValueError('original assignment manifest changed')
    rows=[];traces=[];ids=set()
    for job in assigned:
        path=output/job['attempt_id'];record=path/'record.json'
        if not record.exists():
            rows.append(dict(job=job,recorded=False,category=None));continue
        row=json.loads(record.read_text())
        if row['job']!=job:raise ValueError('original assignment changed')
        events=[json.loads(x) for x in (path/'events.jsonl').read_text().splitlines()] if (path/'events.jsonl').exists() else []
        reserved=[e['label'] for e in events if e['event']=='reserved'];called=[e for e in events if e['event']=='calling']
        if reserved not in ([],[job['attempt_id']+':0']) or row['reservations']!=reserved or row['calls']!=[e['label'] for e in called] or len(called)>len(reserved):
            raise ValueError('one original reserve-before-call required')
        if (path/'trace.json').exists():
            trace=json.loads((path/'trace.json').read_text());verified=p.verify(trace,counter)
            if any(row.get(k)!=v for k,v in verified.items()):raise ValueError('record differs from independent Native replay')
            request=json.loads((path/'request.json').read_text());response=json.loads((path/'response.json').read_text())
            if (len(called)!=1 or called[0]['request_sha256']!=trace['request_sha256']
                or p.n.original.digest(request)!=trace['request_sha256'] or response!=trace['response']
                or response['id'] in ids):raise ValueError('original request/reply differs or was reused')
            ids.add(response['id']);traces.append(trace)
        else:
            if row['category'] not in ('provider','budget','execution'):raise ValueError('unreplayed result cannot be semantic')
            if row['unknown_usage'] and (not called or row['generation_tokens'] is not None):raise ValueError('unknown usage cannot be zeroed')
        rows.append(dict(row,recorded=True))
    complete=len(traces)==8 and all(not stops_phase(t['record']) for t in traces)
    evidence=p.verify_phase(traces,counter) if complete else None
    return dict(kind='top_level_paired_qualification_archive',scripted=True,live_evidence=False,assigned=8,rows=rows,
        independently_replayed=len(traces),complete=complete,fitness_eligible=complete,evidence=evidence,selection_passed=False)
