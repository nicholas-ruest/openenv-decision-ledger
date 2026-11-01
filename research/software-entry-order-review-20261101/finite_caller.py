"""Finite two-response paired qualification; no live materializer or provider."""
from concurrent.futures import ThreadPoolExecutor
import copy
import json
import math
import os
from pathlib import Path
import threading
import time
import matched_protocol as p

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
        stream.write(p.d.canonical(value)+'\n');stream.flush();os.fsync(stream.fileno())



def attempt(job,backend,counter,path,deadline,stop,seen,seen_lock):
    path.mkdir(mode=0o700);events=path/'events.jsonl';responses=[];requests=[]
    row=dict(job=job,category='budget',failure_origin='budget_failure',semantic_reward=None,reservations=[],calls=[],response_ids=[],unknown_usage=False,generation_tokens=0,known_generation_tokens=0)
    attempt_deadline=min(deadline,time.monotonic()+600);stage='native_initialization';called=known=False
    try:
        trial=p.Trial(job);generated=observed=0
        for turn in range(2):
            called=known=False;stage='accounting'
            limit=min(6000 if turn==0 else 8096,8192-generated-observed-96)
            if stop.is_set() or time.monotonic()>=attempt_deadline or limit<=0 or counter.context(trial.messages)+limit+96>24576:
                stop.set();break
            payload=dict(copy.deepcopy(p.SAMPLING),messages=copy.deepcopy(trial.messages),max_tokens=limit)
            label=job['attempt_id']+':'+str(turn);stage='reservation'
            backend.reserve(label,28672,limit,attempt_deadline);row['reservations'].append(label)
            event(events,dict(event='reserved',label=label,generation_limit=limit))
            if stop.is_set() or time.monotonic()>=attempt_deadline:stop.set();break
            write(path/('request-'+str(turn)+'.json'),payload);requests.append(payload)
            stage='provider';called=True;row['calls'].append(label)
            event(events,dict(event='calling',label=label,request_sha256=p.digest(payload),generation_limit=limit))
            response=backend.call(payload,min(360,attempt_deadline-time.monotonic()),job,turn)
            stage='response_validation';backend.check_reply(response)
            usage=response.get('usage',{});identity=response.get('id');choices=response.get('choices')
            if (not isinstance(identity,str) or not identity or not isinstance(choices,list) or len(choices)!=1
                or any(type(usage.get(k)) is not int or usage[k]<0 for k in ('prompt_tokens','completion_tokens'))):raise ValueError('known original response and usage required')
            with seen_lock:
                if identity in seen:raise ValueError('response reuse')
                seen.add(identity)
            known=True;generated+=usage['completion_tokens'];row.update(generation_tokens=generated,known_generation_tokens=generated)
            row['response_ids'].append(identity);responses.append(response)
            write(path/('response-'+str(turn)+'.json'),response);event(events,dict(event='response_received',response_id=identity))
            backend.check_message(choices[0]['message']);stage='accounting'
            if usage['completion_tokens']>limit or usage['prompt_tokens']>28672 or usage['prompt_tokens']+usage['completion_tokens']>24576:raise ValueError('actual token/context overrun')
            stage='native_processing';result=trial.consume(choices[0]['message'],choices[0].get('finish_reason'))
            observed+=sum(counter.count(p.d.canonical(x)) for x in result['new_observations'])
            stage='accounting'
            if generated+observed>8192 or usage['prompt_tokens']+usage['completion_tokens']+sum(counter.count(p.d.canonical(x)) for x in result['new_observations'])>24576 or counter.context(trial.messages)>24576:raise ValueError('all observations must fit original budgets')
            if time.monotonic()>=attempt_deadline:stop.set();break
            if trial.finished:
                stage='native_replay';trace=p.observe(job,responses,counter);verified=p.verify(trace,counter)
                if trace['requests']!=requests:raise ValueError('original requests changed')
                row.update(verified)
                if time.monotonic()>=attempt_deadline:
                    row.update(category='budget',failure_origin='budget_failure',semantic_reward=None);stop.set()
                else:
                    write(path/'trace.json',trace)
                    if stops_phase(verified):stop.set()
                break
    except Exception as exc:
        row['unknown_usage']=called and not known
        if row['unknown_usage']:row['generation_tokens']=None
        category='budget' if stage in ('reservation','accounting') else 'provider' if stage in ('provider','response_validation') else 'execution'
        row.update(category=category,failure_origin=category+'_failure' if category!='execution' else 'native_execution_unverified',semantic_reward=None)
        event(events,dict(event='failure',stage=stage,error_type=type(exc).__name__,unknown_usage=row['unknown_usage']))
        stop.set()
    write(path/'record.json',row);return row


def run(backend,counter,output,deadline):
    if backend.scripted is not True:raise ValueError('scripted qualification only; live source/case unsealed')
    output=Path(output)
    if output.exists() or type(deadline) not in (float,int) or not math.isfinite(deadline) or not 0<deadline-time.monotonic()<=1200:raise ValueError('fresh archive and original phase deadline required')
    backend.admit([28672]*16,8096,deadline);output.mkdir(mode=0o700,parents=True)
    assigned=p.jobs('qualification');write(output/'assignments.json',assigned)
    stop=threading.Event();seen=set();lock=threading.Lock();rows=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for pair in range(4):
            if stop.is_set() or time.monotonic()>=deadline:break
            futures=[pool.submit(attempt,j,backend,counter,output/j['attempt_id'],deadline,stop,seen,lock) for j in assigned[2*pair:2*pair+2]]
            rows.extend(f.result() for f in futures)
    report=assemble(output,counter)
    summary=dict(scripted=True,live_evidence=False,assigned=8,recorded=len(rows),calls=sum(len(r['calls']) for r in rows),unknown_usage_calls=sum(r['unknown_usage'] for r in rows),complete=report['complete'] and not stop.is_set() and time.monotonic()<deadline,max_inflight_requests=2,retries=0,selection_passed=False)
    write(output/'complete.json',summary);return rows,summary


def assemble(output,counter):
    output=Path(output);assigned=p.jobs('qualification')
    if json.loads((output/'assignments.json').read_text())!=assigned:raise ValueError('original assignment manifest changed')
    rows=[];traces=[];ids=set()
    for job in assigned:
        path=output/job['attempt_id']
        events=[json.loads(x) for x in (path/'events.jsonl').read_text().splitlines()] if (path/'events.jsonl').exists() else []
        if not (path/'record.json').exists():
            called=sum(e['event']=='calling' for e in events);received=sum(e['event']=='response_received' for e in events)
            rows.append(dict(job=job,recorded=False,category=None,observed_calls=called,unknown_usage=received<called));continue
        row=json.loads((path/'record.json').read_text())
        reserved=[e['label'] for e in events if e['event']=='reserved'];calls=[e for e in events if e['event']=='calling']
        expected=[job['attempt_id']+':'+str(i) for i in range(len(reserved))]
        if row['job']!=job or len(reserved)>2 or reserved!=expected or row['reservations']!=reserved or [e['label'] for e in calls]!=reserved[:len(calls)] or len(calls)>len(reserved) or row['calls']!=[e['label'] for e in calls]:raise ValueError('original sequential reserve-before-call required')
        received=[e['response_id'] for e in events if e['event']=='response_received']
        reserve_at=[i for i,e in enumerate(events) if e['event']=='reserved'];call_at=[i for i,e in enumerate(events) if e['event']=='calling'];reply_at=[i for i,e in enumerate(events) if e['event']=='response_received']
        if (received!=row['response_ids'] or len(received)>len(calls)
            or any(reserve_at[i]>=index for i,index in enumerate(call_at))
            or any(call_at[i]>=index for i,index in enumerate(reply_at))
            or (len(reserve_at)==2 and (not reply_at or reply_at[0]>=reserve_at[1]))):raise ValueError('original local reserve/call/reply order changed')
        known_cost=0
        for turn,identity in enumerate(received):
            response=json.loads((path/('response-'+str(turn)+'.json')).read_text())
            if response['id']!=identity:raise ValueError('original known reply identity differs')
            known_cost+=response['usage']['completion_tokens']
        if known_cost!=row['known_generation_tokens'] or (not row['unknown_usage'] and known_cost!=row['generation_tokens']):raise ValueError('known usage prefix changed')
        if (path/'trace.json').exists():
            trace=json.loads((path/'trace.json').read_text());verified=p.verify(trace,counter)
            if any(row.get(k)!=v for k,v in verified.items()) or trace['job']!=job or len(calls)!=len(trace['responses']):raise ValueError('record differs from independent replay')
            for turn,(request,response) in enumerate(zip(trace['requests'],trace['responses'])):
                if (json.loads((path/('request-'+str(turn)+'.json')).read_text())!=request or json.loads((path/('response-'+str(turn)+'.json')).read_text())!=response or calls[turn]['request_sha256']!=p.digest(request) or calls[turn]['generation_limit']!=request['max_tokens'] or response['id'] in ids):raise ValueError('original request/reply differs or reused')
                ids.add(response['id'])
            traces.append(trace)
        else:
            if row['category'] not in ('provider','budget','execution') or row.get('semantic_reward') is not None:raise ValueError('unreplayed outcome cannot be semantic')
            if row['unknown_usage'] and (len(row['calls'])<=len(row['response_ids']) or row['generation_tokens'] is not None):raise ValueError('unknown usage cannot be zeroed')
        rows.append(dict(row,recorded=True))
    complete=len(traces)==8 and all(not stops_phase(t['record']) for t in traces)
    return dict(kind='entry_order_finite_qualification_archive',scripted=True,live_evidence=False,assigned=8,rows=rows,independently_replayed=len(traces),complete=complete,evidence=p.verify_phase(traces,counter) if complete else None,selection_passed=False)
