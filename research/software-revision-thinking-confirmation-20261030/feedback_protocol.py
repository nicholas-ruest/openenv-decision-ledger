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
from mandatory_environment import RequiredReviewEnvironment,ProposalAction
from terminal_audit import classify
from pydantic import ValidationError

class Trial:
    def __init__(self,job):
        self.job=copy.deepcopy(job);self.env=RequiredReviewEnvironment(arm='field_contract')
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
            if self.turn!=2:raise ValueError('mandatory first review bypassed')
            self.closed=True;return dict(classify(self.env,obs),done=True)
        if self.turn!=1 or obs['stage']!='revision' or obs['remaining_responses']!=1 or obs['reward']!=0:raise ValueError('required review contract changed')
        return dict(category='awaiting_revision',done=False,native_reward=0,semantic_reward=None)

canonical=native.canonical
digest=native.digest
NAMESPACE='revision-thinking-20261030'
ARMS=('thinking_off','revision_thinking')
SEEDS={'screen':2860000,'confirmation':2870000}
SAMPLING=dict(model='Qwen/Qwen3.8-27B:deepinfra',temperature=0.7,
    response_format=dict(type='json_object'),chat_template_kwargs=dict(enable_thinking=False))

def schedule(phase):
    if phase not in SEEDS:raise ValueError('frozen phase required')
    rows=[]
    for sample in range(4):
        for arm in ARMS if sample%2==0 else reversed(ARMS):
            job=dict(namespace=NAMESPACE,phase=phase,task_id='software_repair-ignore-d2',
                seed=SEEDS[phase],sample=sample,arm=arm)
            rows.append(dict(job,attempt_id=digest(job)))
    return rows

def sampling_for(job,turn):
    if job not in schedule(job['phase']) or type(turn) is not int or turn not in (0,1):
        raise ValueError('frozen job and turn required')
    value=copy.deepcopy(SAMPLING)
    value['chat_template_kwargs']['enable_thinking']=(job['arm']=='revision_thinking' and turn==1)
    return value

def capture(job):
    if job not in schedule('confirmation'):raise ValueError('reserved confirmation jobs only')
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
        all_confirmation_jobs=jobs,frozen_confirmation_jobs=schedule('confirmation'),
        confirmation_groups=[dict(task_id=jobs[0]['task_id'],seed=SEEDS['confirmation'],
            problem_sha256=arms[ARMS[0]]['problem_sha256'],arms=arms)],
        confirmation_observations_materialized=True,phase='confirmation',sampling=SAMPLING,
        first_proposal_sampling={arm:sampling_for(next(j for j in jobs if j['arm']==arm),0) for arm in ARMS},
        max_attempts=8,max_calls=16,max_calls_per_chunk=4,retries=0,
        first_generation_limit=6000,completion_with_observations=8192,context=24576,
        reserved_final_observation_tokens=96,attempt_wall_seconds=600,
        intervention='Required two-response review in both arms, identical first prompt/content-only action schema. Both arms receive identical public-field feedback and public-contract parent-status reminder. Both first proposals request thinking false; only the treatment revision after public feedback requests thinking true. No token, context, route, grader or source difference; actual provider thinking behavior requires separate observation.',
        selection='Complete eight assigned attempts, all actual identities/usage verified, no provider or budget failure, positive full-solve delta and nonnegative semantic delta. Freeze selection before fresh confirmation; no redesign on confirmation.',
        limitations='One procedural screen case and four samples per arm. Native environment observations; production Arena wrapper equivalence and thinking behavior are not attested. No training, transfer or leaderboard claim.')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--chunk',type=int,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--screen-gate',type=Path,required=True);p.add_argument('--screen-gate-sha256',required=True);a=p.parse_args()
    from confirmation_gate import verify_gate
    verify_gate(a.screen_gate,a.screen_gate_sha256)
    value=bundle(a.chunk)
    with a.output.open('x') as f:json.dump(value,f,indent=2)
    print(digest(value))
