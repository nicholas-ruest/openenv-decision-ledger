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
Trial=native.Trial
canonical=native.canonical
digest=native.digest
NAMESPACE='native-feedback8k-20261029'
ARMS=('review_control','public_check')
SEEDS={'screen':2660000,'confirmation':2670000}
SAMPLING=dict(model='Qwen/Qwen3.8-27B:deepinfra',temperature=0.7,
    response_format=dict(type='json_object'),chat_template_kwargs=dict(enable_thinking=True))

def schedule(phase):
    if phase not in SEEDS:raise ValueError('frozen phase required')
    rows=[]
    for sample in range(4):
        for arm in ARMS if sample%2==0 else reversed(ARMS):
            job=dict(namespace=NAMESPACE,phase=phase,task_id='software_repair-ignore-d3',
                seed=SEEDS[phase],sample=sample,arm=arm)
            rows.append(dict(job,attempt_id=digest(job)))
    return rows

def capture(job):
    if job not in schedule('screen'):raise ValueError('confirmation observations remain unmaterialized')
    trial=Trial(job)
    reset=json.loads(trial.messages[1]['content'])
    problem={k:reset[k] for k in ('task_id','prompt','source','examples')}
    return dict(messages=copy.deepcopy(trial.messages),prompt_sha256=digest(trial.messages),
        problem_sha256=digest(problem))

def bundle(chunk):
    if type(chunk) is not int or chunk not in range(4):raise ValueError('four exact chunks required')
    jobs=schedule('screen');arms={arm:capture(next(j for j in jobs if j['arm']==arm)) for arm in ARMS}
    if arms[ARMS[0]]!=arms[ARMS[1]]:raise ValueError('first prompts must match exactly')
    return dict(namespace=NAMESPACE,chunk=chunk,screen_jobs=[j for j in jobs if j['sample']==chunk],
        all_screen_jobs=jobs,confirmation_jobs=schedule('confirmation'),
        screen_groups=[dict(task_id=jobs[0]['task_id'],seed=SEEDS['screen'],
            problem_sha256=arms[ARMS[0]]['problem_sha256'],arms=arms)],
        confirmation_observations_materialized=False,sampling=SAMPLING,
        max_attempts=8,max_calls=16,max_calls_per_chunk=4,retries=0,
        first_generation_limit=6000,completion_with_observations=8192,context=24576,
        reserved_final_observation_tokens=96,attempt_wall_seconds=600,
        intervention='Computed public-example feedback versus neutral review, identical first prompt and two-response action schema. No helper-preservation intervention.',
        selection='Complete eight assigned attempts, all actual identities/usage verified, no provider or budget failure, positive full-solve delta and nonnegative semantic delta. Freeze selection before fresh confirmation; no redesign on confirmation.',
        limitations='One procedural screen case and four samples per arm. Native environment observations; production Arena wrapper equivalence and thinking behavior are not attested. No training, transfer or leaderboard claim.')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--chunk',type=int,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    value=bundle(a.chunk)
    with a.output.open('x') as f:json.dump(value,f,indent=2)
    print(digest(value))
