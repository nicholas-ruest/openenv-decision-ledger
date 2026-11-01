"""Matched failure-advice qualification and independent replay; no paid API."""
import copy
import hashlib
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research/software-helper-controller-20261031'))
# Reuse the pinned Native import setup, not the closed helper intervention.
import matched_protocol as native_paths
from failure_advice import ARMS,FailureAdviceTrial,canonical,observation_tokens

TASK='software_repair-ignore-d2'
NAMESPACE='public-failure-advice-20261031'
SAMPLING=copy.deepcopy(native_paths.SAMPLING)
SEEDS=dict(screen=3160000,confirmation=3170000,qualification=3100000)


def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()


def jobs(phase):
    if phase not in SEEDS:raise ValueError('explicit phase required')
    out=[]
    for sample in range(4):
        for arm in ARMS if sample%2==0 else reversed(ARMS):
            value=dict(namespace=NAMESPACE,phase=phase,task_id=TASK,seed=SEEDS[phase],sample=sample,arm=arm)
            out.append(dict(value,attempt_id=digest(value)))
    return out


def sampling_for(job,turn):
    if job not in jobs(job['phase']) or type(turn) is not int or turn not in (0,1):raise ValueError('original assignment and response only')
    return copy.deepcopy(SAMPLING)


class QualificationTrial(FailureAdviceTrial):
    def __init__(self,job):
        if job not in jobs('qualification'):raise ValueError('existing qualification case only')
        from action_example_protocol import Trial,schedule
        super().__init__(Trial(schedule('screen')[0]),arm=job['arm'])


def materialize(job,case_audit=None,case_sha256=None):
    from failure_materializer import materialize as construct
    return construct(job,case_audit,case_sha256)


def plan():
    return dict(screen_jobs=jobs('screen'),confirmation_jobs=jobs('confirmation'),sampling=copy.deepcopy(SAMPLING),
        first_generation_limit=6000,completion_with_observations=8192,context=24576,final_observation_reserve=96,
        max_attempts=8,max_model_calls=16,attempt_wall_seconds=600,phase_wall_seconds=1200,request_wall_seconds=360,
        retries=0,paid_execution_ready=False,screen_materialized=False,confirmation_materialized=False,
        selection='Complete eight original assignments; known usage; no provider/budget failure; verified advice exposure; positive full-outcome delta and nonnegative semantic delta before unchanged disjoint confirmation.',
        is_training=False,model_improvement=False,leaderboard_gain=False)


class ObservationBudgetExceeded(ValueError):pass


def _process(trial,response,turn,counter,generated,native,advice):
    limit=6000 if turn==0 else 8192-generated-native-advice-96
    usage=response.get('usage',{});choices=response.get('choices')
    if (not isinstance(response.get('id'),str) or not response['id']
            or any(type(usage.get(k)) is not int or usage[k]<0 for k in ('prompt_tokens','completion_tokens'))
            or not isinstance(choices,list) or len(choices)!=1 or limit<=0
            or usage['completion_tokens']>limit or usage['prompt_tokens']>28672
            or usage['prompt_tokens']+usage['completion_tokens']>24576
            or counter.context(trial.messages)+limit+96>24576):raise ValueError('original verified usage/context bound required')
    e=dict(response=copy.deepcopy(response),prompt_sha256=digest(trial.messages),requested_max_tokens=limit,
        native_observations=[],advice_observations=[],advice_delivered=False)
    choice=choices[0];generated+=usage['completion_tokens'];reward=None;terminal_reward=None
    if choice['finish_reason']=='length':category='truncation';done=True
    elif choice['finish_reason']=='stop':
        result=trial.consume(choice['message']['content'],finish_reason='stop')
        e.update(native_observations=result['new_observations'],advice_observations=result['advice_observations'],advice_delivered=result['advice_delivered'])
        native+=sum(counter.count(canonical(x)) for x in result['new_observations'])
        advice+=sum(counter.count(canonical(x)) for x in result['advice_observations'])
        category=result['category'];done=result['done'];reward=result.get('semantic_reward');terminal_reward=result.get('native_reward') if done else None
    else:raise ValueError('provider failure requires finite caller handling')
    if generated+native+advice>8192 or counter.context(trial.messages)>24576:raise ObservationBudgetExceeded('all actual observations consume original limits')
    return e,generated,native,advice,category,done,reward,terminal_reward


def observe_scripted(job,responses,counter):
    return _observe(job,responses,counter,QualificationTrial(job),True,{})


def _observe(job,responses,counter,trial,scripted,metadata):
    events=[];requests=[];generated=native=advice=0;done=False;ids=set()
    for turn,response in enumerate(responses):
        if turn>=2 or done or response.get('id') in ids:raise ValueError('no replay, duplicate reply or extra response')
        ids.add(response.get('id'))
        limit=6000 if turn==0 else 8192-generated-native-advice-96
        payload=dict(sampling_for(job,turn),messages=trial.messages,max_tokens=limit)
        requests.append(dict(request_sha256=digest(payload),prompt_sha256=digest(trial.messages),requested_max_tokens=limit))
        e,generated,native,advice,category,done,reward,terminal_reward=_process(trial,response,turn,counter,generated,native,advice)
        events.append(e)
    if not done:raise ValueError('incomplete assigned attempt is not a semantic outcome')
    record=dict(category=category,generation_tokens=generated,native_observation_tokens=native,advice_observation_tokens=advice,
        completion_with_observations=generated+native+advice,model_responses=len(events),
        advice_deliveries=sum(e['advice_delivered'] for e in events),semantic_reward=reward,terminal_reward_observed=terminal_reward,
        finish_reason=events[-1]['response']['choices'][0]['finish_reason'])
    result=dict(job=copy.deepcopy(job),scripted=scripted,live_evidence=not scripted,events=events,record=record)
    if not scripted:result.update(metadata,requests=requests)
    return result


def verify(trace,counter):
    if trace.get('scripted') is not True or trace.get('live_evidence') is not False or trace['job'] not in jobs('qualification'):
        raise ValueError('qualification traces cannot be relabelled as live evidence')
    # Fresh Native instance; reconstruct every actual prompt, observation and cost.
    expected=observe_scripted(trace['job'],[e['response'] for e in trace['events']],counter)
    if expected!=trace:raise ValueError('original transcript, advice exposure, grading or accounting changed')
    return dict(verified=True,scripted=True,live_evidence=False,**expected['record'])


def verify_phase(traces,counter):
    assigned=jobs('qualification')
    if len(traces)!=8 or [t['job'] for t in traces]!=assigned:raise ValueError('all eight ordered original assignments required')
    ids=[e['response']['id'] for t in traces for e in t['events']]
    if len(ids)!=len(set(ids)):raise ValueError('cross-attempt reply reuse')
    rows=[dict(job=t['job'],**verify(t,counter)) for t in traces]
    return dict(kind='failure_advice_qualification',scripted=True,live_evidence=False,assigned=8,rows=rows,
        all_assigned_in_denominator=True,selection_passed=False,model_improvement=False,leaderboard_gain=False)


def verify_screen(trace,counter,case_audit,case_sha256):
    from failure_materializer import execution_hashes
    metadata=dict(case_audit_sha256=case_sha256,execution_sha256=execution_hashes())
    if (trace.get('scripted') is not False or trace.get('live_evidence') is not True
        or trace['job'] not in jobs('screen') or any(trace.get(k)!=v for k,v in metadata.items())):
        raise ValueError('exact sealed original screen trace required')
    expected=_observe(trace['job'],[e['response'] for e in trace['events']],counter,
        materialize(trace['job'],case_audit,case_sha256),False,metadata)
    if trace!=expected:raise ValueError('request, advice, Native outcome, source or accounting changed')
    return dict(verified=True,scripted=False,live_evidence=True,**expected['record'])
