"""Frozen matched scripted replay; no provider, live cases or financial authority."""
import copy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import order_diagnostic as d
from revision_environment import RevisionEnvironment,plan as environment_plan
from repair_env.direct_environment import DirectRepairAction
sys.path.insert(0,str(d.ROOT/'research/software-terminal-audit-20261028'))
from terminal_audit import classify

NAMESPACE='public-entry-order-review-20261101'
SEEDS=dict(qualification=2560000,screen=3220000,confirmation=3230000)
SAMPLING=dict(model='Qwen/Qwen3.8-27B:deepinfra',temperature=.7,response_format={'type':'json_object'})


def digest(value):return hashlib.sha256(d.canonical(value).encode()).hexdigest()


def jobs(phase):
    if phase not in SEEDS:raise ValueError('explicit original phase required')
    result=[]
    for sample in range(4):
        for arm in d.ARMS if sample%2==0 else reversed(d.ARMS):
            value=dict(namespace=NAMESPACE,phase=phase,task_id='software_repair-ignore-d3',seed=SEEDS[phase],sample=sample,arm=arm)
            result.append(dict(value,attempt_id=digest(value)))
    return result


class Trial:
    def __init__(self,job):
        if job not in jobs('qualification'):raise ValueError('already-seen qualification only; no live trial')
        self.job=copy.deepcopy(job);self.env=RevisionEnvironment(arm=job['arm'])
        initial=self.env.reset(seed=job['seed'],task_id=job['task_id']).model_dump()
        self.problem_sha256=digest({k:v for k,v in initial.items() if k!='prompt'})
        self.messages=[dict(role='system',content='Return exactly one JSON action instance matching this schema. No markdown, diff or tool command. '+d.canonical(DirectRepairAction.model_json_schema())),dict(role='user',content=d.canonical(initial))]
        self.finished=False;self.turn=0

    def consume(self,message,finish_reason):
        if self.finished:raise ValueError('original attempt already ended')
        self.turn+=1;self.messages.append(copy.deepcopy(message))
        if finish_reason!='stop':
            self.finished=True
            return dict(category='truncation' if finish_reason=='length' else 'provider',semantic_reward=None,terminal_reward_observed=None,new_observations=[],failure_origin='model_output_truncation' if finish_reason=='length' else 'provider_failure')
        try:action=DirectRepairAction.model_validate_json(message.get('content'),strict=True)
        except (ValueError,TypeError):
            self.finished=True
            return dict(category='format',semantic_reward=None,terminal_reward_observed=None,new_observations=[],failure_origin='model_output_format')
        native=self.env.step(action).model_dump();self.messages.append(dict(role='user',content=d.canonical(native)))
        if not native['done']:
            return dict(category='awaiting_revision',semantic_reward=None,terminal_reward_observed=None,new_observations=[native],failure_origin=None)
        self.finished=True;result=classify(self.env,native)
        origin='native_semantic_outcome'
        if result['category']=='execution':
            origin='model_program_rejection' if result['compile_rejected'] else 'model_program_runtime_error' if result['hidden_execution_errors']>0 else 'native_execution_unverified'
        return dict(category=result['category'],semantic_reward=result['semantic_reward'],terminal_reward_observed=result['native_reward'],new_observations=[native],failure_origin=origin,native_compile_rejected=result['compile_rejected'],native_runtime_error_observed=result['hidden_execution_errors']>0)


def observe(job,responses,counter):
    if not isinstance(responses,list) or not 1<=len(responses)<=2:raise ValueError('one or two original known replies required')
    trial=Trial(job);initial=copy.deepcopy(trial.messages);generated=observed=0;requests=[];ids=set();steps=[];feedback=None
    for response in responses:
        if trial.finished:raise ValueError('reply after original terminal outcome')
        limit=min(6000 if trial.turn==0 else 8096,8192-generated-observed-96)
        if limit<=0 or counter.context(trial.messages)+limit+96>24576:raise ValueError('original context/completion budget exhausted')
        request=dict(copy.deepcopy(SAMPLING),messages=copy.deepcopy(trial.messages),max_tokens=limit);requests.append(request)
        usage=response.get('usage',{});identity=response.get('id');choices=response.get('choices')
        if (not isinstance(identity,str) or not identity or identity in ids or not isinstance(choices,list) or len(choices)!=1
            or any(type(usage.get(k)) is not int or usage[k]<0 for k in ('prompt_tokens','completion_tokens'))):
            raise ValueError('unique original reply and actual known usage required')
        ids.add(identity)
        if usage['completion_tokens']>limit or usage['prompt_tokens']>28672 or usage['prompt_tokens']+usage['completion_tokens']>24576:
            raise ValueError('actual generation/context budget exceeded')
        message=choices[0].get('message',{})
        if message.get('role')!='assistant' or message.get('tool_calls') or message.get('function_call'):
            raise ValueError('original content-only assistant action required')
        result=trial.consume(message,choices[0].get('finish_reason'))
        tokens=sum(counter.count(d.canonical(x)) for x in result['new_observations']);generated+=usage['completion_tokens'];observed+=tokens
        if (generated+observed>8192 or usage['prompt_tokens']+usage['completion_tokens']+tokens>24576 or counter.context(trial.messages)>24576):
            raise ValueError('all original observations must fit unchanged budgets')
        if result['category']=='awaiting_revision':feedback=json.loads(result['new_observations'][0]['feedback'])
        steps.append(dict(request_sha256=digest(request),generation_limit=limit,generation_tokens=usage['completion_tokens'],native_observation_tokens=tokens,result=result))
    if not trial.finished:raise ValueError('unfinished two-response attempt is not an outcome')
    last=steps[-1]['result'];diagnostic=feedback.get('diagnostic') if feedback else None
    record=dict(category=last['category'],semantic_reward=last['semantic_reward'],terminal_reward_observed=last['terminal_reward_observed'],failure_origin=last['failure_origin'],
        native_compile_rejected=last.get('native_compile_rejected',False),native_runtime_error_observed=last.get('native_runtime_error_observed',False),
        generation_tokens=generated,native_observation_tokens=observed,completion_with_observations=generated+observed,
        model_responses=len(responses),finish_reason=responses[-1]['choices'][0].get('finish_reason'),controller_actions=[],
        computed_relation_exposed=bool(diagnostic and diagnostic.get('kind')=='public_entry_order_relation'),
        usable_relation_counterexample_exposed=bool(diagnostic and diagnostic.get('kind')=='public_entry_order_relation' and diagnostic.get('first_counterexample') is not None))
    return dict(job=copy.deepcopy(job),scripted=True,live_evidence=False,prompt_sha256=digest(initial),problem_sha256=trial.problem_sha256,
        requests=requests,responses=copy.deepcopy(responses),steps=steps,messages=trial.messages,record=record)


def verify(trace,counter):
    if trace.get('scripted') is not True or trace.get('live_evidence') is not False:
        raise ValueError('scripted qualification cannot become live model evidence')
    reconstructed=observe(trace['job'],trace['responses'],counter)
    if trace!=reconstructed:raise ValueError('original requests, responses, Native results or observation costs differ')
    return dict(job=trace['job'],verified=True,scripted=True,live_evidence=False,**reconstructed['record'])


def verify_phase(traces,counter):
    if len(traces)!=8 or [t['job'] for t in traces]!=jobs('qualification'):
        raise ValueError('all eight original counterbalanced assignments required')
    ids=[r['id'] for t in traces for r in t['responses']]
    if len(set(ids))!=len(ids):raise ValueError('cross-attempt reply reuse')
    rows=[verify(t,counter) for t in traces]
    if len({t['prompt_sha256'] for t in traces})!=1 or len({t['problem_sha256'] for t in traces})!=1:
        raise ValueError('identical original first prompt and Native problem required')
    if any(r['computed_relation_exposed'] for r in rows if r['job']['arm']=='relation_only'):
        raise ValueError('control received computed relation feedback')
    return dict(kind='entry_order_review_qualification',scripted=True,live_evidence=False,assigned=8,all_assigned_in_denominator=True,rows=rows,selection_passed=False,model_improvement=False,is_training=False)


def plan():
    value=environment_plan();value.update(namespace=NAMESPACE,sampling=copy.deepcopy(SAMPLING),screen_jobs=jobs('screen'),confirmation_jobs=jobs('confirmation'),
        required_next_step='Qualify finite caller, source/case materializer, original archive replay and actual pinned MetaHarness assessment; live inputs and paid calls stay unsealed.',
        selection='Complete original screen with known usage and raw Native/token/exposure replay, positive full-repair difference and nonnegative all-assignment semantic mean difference, no provider/budget/unverified Native failures; then require unchanged fresh disjoint confirmation. No pooled selected screen/confirmation estimate.')
    return value
