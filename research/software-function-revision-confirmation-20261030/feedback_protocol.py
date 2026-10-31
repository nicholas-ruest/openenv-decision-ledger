"""Frozen computed-public-feedback experiment. No paid execution authority."""
import copy
import importlib.util
import json
import hashlib
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/p) for p in ('research/software-terminal-audit-20261028',
    'research/software-revision-candidate-20261028','research/software-public-check-20261028',
    'integrations/software-repair')]
spec=importlib.util.spec_from_file_location('native_feedback_trial',ROOT/'research/software-matched-inputs-20261028/matched_inputs.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
from function_revision import FunctionRevisionAction as ProposalAction
from function_revision import FunctionRevisionEnvironment
from terminal_audit import classify
from pydantic import ValidationError

class Trial:
    def __init__(self,job):
        self.job=copy.deepcopy(job);self.env=FunctionRevisionEnvironment(arm=job['arm'])
        reset=self.env.reset(task_id=job['task_id'],seed=job['seed']).model_dump()
        self.messages=[dict(role='system',content='Return exactly one JSON action instance matching this schema. No markdown, diff, or tool command. '+native.canonical(ProposalAction.model_json_schema())),dict(role='user',content=native.canonical(reset))]
        self.turn=0;self.closed=False;self.native=[]
    def consume(self,reply):
        if self.closed or self.turn>=2:raise ValueError('no retry/redraw after terminal')
        self.turn+=1
        try:
            if type(reply) is not str:raise ValueError('raw assistant text required')
            action=ProposalAction.model_validate_json(reply,strict=True)
        except (ValidationError,ValueError):
            self.closed=True;return dict(category='format',done=True,native_reward=None,semantic_reward=None)
        obs=self.env.step(action).model_dump();self.native.append(obs)
        self.messages += [dict(role='assistant',content=reply),dict(role='user',content=native.canonical(obs))]
        if obs['done']:
            if self.env._revision_error:
                self.closed=True;return dict(category='edit_rejection',done=True,native_reward=0,semantic_reward=None)
            if self.turn!=2 and action.content:raise ValueError('only an empty action may finish before review')
            self.closed=True;return dict(classify(self.env,obs),done=True)
        if self.turn!=1 or obs['stage']!='revision' or obs['remaining_responses']!=1 or obs['reward']!=0:raise ValueError('required review contract changed')
        return dict(category='awaiting_revision',done=False,native_reward=0,semantic_reward=None)

canonical=native.canonical
digest=native.digest
NAMESPACE='function-revision-policy-20261030'
ARMS=('module_review','function_review')
SEEDS={'screen':3060000,'confirmation':3070000}
SAMPLING=dict(model='Qwen/Qwen3.8-27B:deepinfra',temperature=0.7,
    response_format=dict(type='json_object'))

SELECTION_SHA256='29ad41846a2f8fed3a9537cb677462b5e7ef73f007f08fac7c85445c0ab14cf3'
RESERVED_JOBS_SHA256='79486d11d6ecbb0a75b9c23798eb757784b84f26db3bba826daec02f2db56c16'
CASE_AUDIT_SHA256='7a3db3a2a480aa809c6cfbed4133bd21c2c2212fb237727221db444c818a4abe'

def bound_json(path,expected):
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected:
        raise ValueError('immutable confirmation binding changed')
    return json.loads(raw)

def check_selection(path=None):
    value=bound_json(path or Path(__file__).with_name('screen-selection.json'),SELECTION_SHA256)
    if (value['source']!='8de6b520b342c1595dfae003cfe5e6d87114d8de'
        or value['selection_passed'] is not True or value['all_live_replies_verified'] is not True
        or value['actual_calls']!=14 or value['known_replies']!=14 or value['assigned_attempts']!=8
        or value['full_rate_delta']<=0 or value['semantic_mean_delta']<0
        or value['function_revision_exposure']['function_review']<=0):
        raise ValueError('completed selected original screen required')
    return value

def reserved_jobs(path=None):
    value=bound_json(path or Path(__file__).with_name('reserved-confirmation-jobs.json'),RESERVED_JOBS_SHA256)
    if value!=schedule('confirmation'):
        raise ValueError('original reserved confirmation assignments required')
    return value

def check_case_audit(path):
    """Recompute disjointness from the sealed private task/seed inventory."""
    value=bound_json(path,CASE_AUDIT_SHA256)
    from repair_env.tasks import make_task
    from repair_env.direct_environment import DirectRepairEnvironment
    pairs=value['prior_task_seed_pairs']
    if len(pairs)!=44 or len({tuple(x) for x in pairs})!=44 or pairs!=sorted(pairs):
        raise ValueError('complete sealed prior case inventory required')
    if ['software_repair-ignore-d3',3070000] in pairs:
        raise ValueError('confirmation case was previously materialized')
    past=set()
    for task,seed in pairs:
        t=make_task(task,seed)
        past.update(digest(c.args) for c in t.public+t.hidden)
    t=make_task('software_repair-ignore-d3',3070000)
    current={digest(c.args) for c in t.public+t.hidden}
    obs=DirectRepairEnvironment().reset(task_id=t.task_id,seed=t.seed)
    if (len(past)!=1440 or len(current)!=36 or past&current
        or digest(sorted(past))!=value['prior_input_set_sha256']
        or digest(sorted(current))!=value['new_input_set_sha256']
        or digest(dict(source=obs.source,examples=obs.examples))!=value['new_source_examples_sha256']
        or value['screen_selection_sha256']!=SELECTION_SHA256
        or value['reserved_jobs_sha256']!=RESERVED_JOBS_SHA256):
        raise ValueError('independent disjoint confirmation audit failed')
    return dict(verified=True,prior_cases=44,prior_inputs=1440,new_inputs=36,input_overlap=0,
                case_audit_sha256=CASE_AUDIT_SHA256)

def schedule(phase):
    if phase not in SEEDS:raise ValueError('frozen phase required')
    rows=[]
    for sample in range(4):
        for arm in ARMS if sample%2==0 else reversed(ARMS):
            job=dict(namespace=NAMESPACE,phase=phase,task_id='software_repair-ignore-d3',
                seed=SEEDS[phase],sample=sample,arm=arm)
            rows.append(dict(job,attempt_id=digest(job)))
    return rows

def sampling_for(job,turn):
    if job not in schedule(job['phase']) or type(turn) is not int or turn not in (0,1):
        raise ValueError('frozen job and turn required')
    return copy.deepcopy(SAMPLING)

def capture(job):
    check_selection()
    if job not in schedule('confirmation'):raise ValueError('only original reserved confirmation jobs admitted')
    trial=Trial(job)
    reset=json.loads(trial.messages[1]['content'])
    problem={k:reset[k] for k in ('task_id','prompt','source','examples')}
    return dict(messages=copy.deepcopy(trial.messages),prompt_sha256=digest(trial.messages),
        problem_sha256=digest(problem))

def bundle(chunk):
    if type(chunk) is not int or chunk not in range(4):raise ValueError('four exact chunks required')
    jobs=schedule('confirmation');arms={arm:capture(next(j for j in jobs if j['arm']==arm)) for arm in ARMS}
    if arms[ARMS[0]]!=arms[ARMS[1]]:raise ValueError('first prompts must match exactly')
    return dict(namespace=NAMESPACE,chunk=chunk,confirmation_jobs=[j for j in jobs if j['sample']==chunk],
        all_confirmation_jobs=jobs,frozen_confirmation_jobs=reserved_jobs(),
        confirmation_groups=[dict(task_id=jobs[0]['task_id'],seed=SEEDS['confirmation'],
            problem_sha256=arms[ARMS[0]]['problem_sha256'],arms=arms)],
        confirmation_observations_materialized=True,phase="confirmation",screen_selection=check_selection(),sampling=SAMPLING,
        first_proposal_sampling={arm:sampling_for(next(j for j in jobs if j['arm']==arm),0) for arm in ARMS},
        max_attempts=8,max_calls=16,max_calls_per_chunk=4,retries=0,
        first_generation_limit=6000,completion_with_observations=8192,context=24576,
        reserved_final_observation_tokens=96,attempt_wall_seconds=600,
        intervention='Both arms have the same action schema, first prompt, public-field and runtime feedback, module hash, Native interpreter, sampler and total budgets. Both can use full modules or final hash-bound function blocks. Only treatment review advice encourages localized function-block revisions.',
        selection='Complete all eight reserved confirmation assignments with all actual identities/usage verified, no provider or budget failure, positive full-solve delta and nonnegative semantic delta, and at least one actual successfully applied treatment function-block revision. The intervention, Native package, sampler and budgets are unchanged from the selected screen.',
        limitations='One fresh disjoint procedural confirmation case and four samples per arm. Native environment observations; production Arena wrapper equivalence and thinking behavior are not attested. No training, transfer or leaderboard claim.')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--chunk',type=int,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    value=bundle(a.chunk)
    with a.output.open('x') as f:json.dump(value,f,indent=2)
    print(digest(value))
