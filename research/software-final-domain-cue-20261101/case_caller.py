"""Prepared case-bound finite caller. No qualified live supervisor entry point."""
import ast,copy,json,math,os,threading,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import case_archive as archive
import case_transport as transport
gate=transport.bridge.gate
for name,module in [('case_archive',archive),('case_transport',transport)]:
    if Path(module.__file__).resolve()!=Path(__file__).with_name(name+'.py').resolve():raise ValueError('exact sibling integration required')


def _support():
    # Called only after case refusal/validation; Native stays out of the parent entry.
    runtime=archive.replay.binding._runtime()
    p=SimpleNamespace(SAMPLING=runtime.SAMPLING,digest=runtime.p.digest,d=runtime.p.d)
    path=Path(__file__).with_name('finite_caller.py')
    tree=ast.parse(path.read_text());names={'stops_phase','write','event'}
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    if {n.name for n in nodes}!=names or len(nodes)!=3:raise ValueError('original finite policy helpers required')
    namespace=dict(p=p,time=time,json=json,os=os)
    # Execute only these trusted original framework helpers, never submitted code.
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),namespace)
    return SimpleNamespace(p=p,**{n:namespace[n] for n in names})


def attempt(job,backend,counter,path,deadline,stop,seen,seen_lock,args):
    case=gate.require_case(args)
    if type(backend) is not transport._AtomicOriginal or gate.digest(job) not in [gate.digest(j) for j in case['jobs']]:raise ValueError('exact bound transport and assignment required')
    c=_support();p=c.p;write=c.write;event=c.event;stops_phase=c.stops_phase
    path.mkdir(mode=0o700);events=path/'events.jsonl';responses=[];requests=[]
    row=dict(job=job,category='budget',failure_origin='budget_failure',semantic_reward=None,reservations=[],calls=[],response_ids=[],unknown_usage=False,generation_tokens=0,known_generation_tokens=0)
    attempt_deadline=min(deadline,time.monotonic()+600);stage='native_initialization';called=known=False
    try:
        trial=archive.replay.binding.materialize(job,args)
        generated=observed=0
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
                stage='native_replay'
                trace=archive.replay.reconstruct(job,responses,counter,args);verified=archive.replay.verify(trace,counter,args)
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


def phase(args,backend,output,deadline):
    case=gate.require_case(args)
    if (type(backend) is not transport._AtomicOriginal
        or any(backend.jobs.get(j['attempt_id'])!=gate.digest(j) for j in case['jobs'])):
        raise ValueError('same source/case bound original transport required')
    output=Path(output)
    if (output.exists() or type(deadline) not in (int,float) or not math.isfinite(deadline)
        or not 0<deadline-time.monotonic()<=1200):raise ValueError('fresh output and original deadline required')
    backend.admit([28672]*16,8096,deadline)
    c=_support();counter=backend.counter;output.mkdir(mode=0o700,parents=True)
    c.write(output/'assignments.json',case['jobs'])
    stop=threading.Event();seen=set();lock=threading.Lock();rows=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for pair in range(4):
            if stop.is_set() or time.monotonic()>=deadline:break
            futures=[pool.submit(attempt,j,backend,counter,output/j['attempt_id'],deadline,stop,seen,lock,args)
                     for j in case['jobs'][2*pair:2*pair+2]]
            rows.extend(f.result() for f in futures)
    report=archive.assemble(output,counter,args)
    summary=dict(kind='case_bound_finite_phase',assigned=8,recorded=len(rows),
        observed_calls=sum(len(r['calls']) for r in rows),unknown_usage_calls=sum(r['unknown_usage'] for r in rows),
        all_terminal_attempts_reconstructed=report['all_terminal_attempts_reconstructed'],
        complete=report['all_terminal_attempts_reconstructed'] and not stop.is_set() and time.monotonic()<deadline,
        max_inflight_requests=2,retries=0,provider_provenance_attested=False,
        live_supervisor_binding_qualified=False,selection_passed=False,model_improvement=False)
    c.write(output/'complete.json',summary)
    return rows,summary,report


def run_screen(*args,**kwargs):
    raise ValueError('live worker/supervisor binding unqualified; no execution entry')

