"""Frozen computed-public-feedback experiment. No paid execution authority."""
import copy
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/p) for p in ('research/software-terminal-audit-20261028',
    'research/software-revision-candidate-20261028','research/software-public-check-20261028',
    'integrations/software-repair')]
spec=importlib.util.spec_from_file_location('native_feedback_trial',ROOT/'research/software-matched-inputs-20261028/matched_inputs.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
from mandatory_environment import ProposalAction
from contract_environment import ContractEnvironment as DiagnosticEnvironment, CONTRACT_NOTE
from terminal_audit import classify
from pydantic import ValidationError

class Trial:
    def __init__(self,job):
        self.job=copy.deepcopy(job);self.env=DiagnosticEnvironment(arm=job['arm'])
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
            if self.turn!=2 and action.content:raise ValueError('only an empty action may finish before review')
            self.closed=True;return dict(classify(self.env,obs),done=True)
        if self.turn!=1 or obs['stage']!='revision' or obs['remaining_responses']!=1 or obs['reward']!=0:raise ValueError('required review contract changed')
        return dict(category='awaiting_revision',done=False,native_reward=0,semantic_reward=None)

canonical=native.canonical
digest=native.digest
NAMESPACE='output-contract-focus-20261030'
ARMS=('standard_contract','explicit_contract')
SEEDS={'screen':3080000,'confirmation':3090000}
SAMPLING=dict(model='Qwen/Qwen3.8-27B:deepinfra',temperature=0.7,
    response_format=dict(type='json_object'))

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
    if job not in schedule('screen'):raise ValueError('confirmation observations remain unmaterialized')
    trial=Trial(job)
    reset=json.loads(trial.messages[1]['content'])
    if job['arm']=='explicit_contract':
        if not reset['prompt'].endswith(CONTRACT_NOTE):raise ValueError('exact treatment note required')
        reset['prompt']=reset['prompt'][:-len(CONTRACT_NOTE)]
    problem={k:reset[k] for k in ('task_id','prompt','source','examples')}
    return dict(messages=copy.deepcopy(trial.messages),prompt_sha256=digest(trial.messages),
        problem_sha256=digest(problem))

def bundle(chunk):
    if type(chunk) is not int or chunk not in range(4):raise ValueError('four exact chunks required')
    jobs=schedule('screen');arms={arm:capture(next(j for j in jobs if j['arm']==arm)) for arm in ARMS}
    if arms[ARMS[0]]['problem_sha256']!=arms[ARMS[1]]['problem_sha256']:raise ValueError('original task must match exactly')
    if arms[ARMS[0]]['prompt_sha256']==arms[ARMS[1]]['prompt_sha256']:raise ValueError('first-prompt intervention required')
    return dict(namespace=NAMESPACE,chunk=chunk,screen_jobs=[j for j in jobs if j['sample']==chunk],
        all_screen_jobs=jobs,confirmation_jobs=schedule('confirmation'),
        screen_groups=[dict(task_id=jobs[0]['task_id'],seed=SEEDS['screen'],
            problem_sha256=arms[ARMS[0]]['problem_sha256'],arms=arms)],
        confirmation_observations_materialized=False,sampling=SAMPLING,
        first_proposal_sampling={arm:sampling_for(next(j for j in jobs if j['arm']==arm),0) for arm in ARMS},
        max_attempts=8,max_calls=16,max_calls_per_chunk=4,retries=0,
        first_generation_limit=6000,completion_with_observations=8192,context=24576,
        reserved_final_observation_tokens=96,attempt_wall_seconds=600,
        intervention='Both arms have the same original task, code action schema, public field/runtime feedback, review advice, Native package, sampler and total budgets. Only treatment adds a fixed output-contract note to the initial reset prompt: return exactly the original entry paths, use parent paths only internally, and return boolean values.',
        selection='Complete eight assigned attempts, all actual identities/usage verified, no provider or budget failure, positive full-solve delta and nonnegative semantic delta. The exact initial treatment note must be bound in every treatment request; no hidden-case or reference-derived advice. Freeze selection before fresh confirmation; no redesign on confirmation.',
        limitations='One procedural screen case and four samples per arm. Native environment observations; production Arena wrapper equivalence and thinking behavior are not attested. No training, transfer or leaderboard claim.')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--chunk',type=int,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    value=bundle(a.chunk)
    with a.output.open('x') as f:json.dump(value,f,indent=2)
    print(digest(value))
