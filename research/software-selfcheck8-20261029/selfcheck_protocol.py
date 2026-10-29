"""Separate eight-call self-tracing-prompt screen; shared full-module action and SSE route."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/p) for p in ('research/software-function-block-protocol-20261028',
    'research/software-function-edit-20261028','research/software-terminal-audit-20261028',
    'integrations/software-repair')]
import protocol as original
from function_edit import FunctionEditEnvironment,FunctionEditAction,TARGETS
from repair_env.direct_environment import DirectRepairEnvironment,DirectRepairAction
from terminal_audit import classify

canonical=original.canonical
digest=original.digest
ARMS=('neutral_review','public_example_selfcheck')
NAMESPACE='selfcheck8-20261029'
TARGETS={'software_repair-ignore-d3':'classify_ignore'}
SEEDS={'screen':(2560000,),'confirmation':(2570000,)}
SAMPLING=copy.deepcopy(original.SAMPLING)
SAMPLING['max_tokens']=4000

def schedule(phase):
    rows=[]
    for sample in range(4):
        for index,task in enumerate(TARGETS):
            for arm in ARMS if sample%2==0 else reversed(ARMS):
                identity=dict(namespace=NAMESPACE,phase=phase,sample=sample,
                    task_id=task,seed=SEEDS[phase][index],arm=arm)
                rows.append(dict(identity,attempt_id=digest(identity)))
    return rows

def capture(task,seed,arm):
    if arm not in ARMS:raise ValueError('explicit selfcheck arm required')
    value=original.capture(task,seed,'full_module')
    instruction=('Before finalizing, trace your proposed module through all six supplied public examples and compare every output field. Fix any mismatch you find. Satisfy the complete contract beyond those examples.' if arm=='public_example_selfcheck' else 'Before finalizing, review your proposed module carefully against the complete contract. Fix any error you find. Satisfy the complete contract beyond the supplied examples.')
    value['messages'][0]['content']+=' '+instruction
    value['prompt_sha256']=digest(value['messages'])
    value['request']=dict(copy.deepcopy(SAMPLING),messages=value['messages'])
    return value

def bundle():
    groups=[]
    for index,task in enumerate(TARGETS):
        seed=SEEDS['screen'][index]
        arms={arm:capture(task,seed,arm) for arm in ARMS}
        if arms[ARMS[0]]['problem']!=arms[ARMS[1]]['problem']:
            raise ValueError('problem differs across arms')
        groups.append(dict(task_id=task,seed=seed,
            problem_sha256=arms[ARMS[0]]['problem_sha256'],arms=arms))
    return dict(namespace=NAMESPACE,screen_jobs=schedule('screen'),
        confirmation_jobs=schedule('confirmation'),screen_groups=groups,
        confirmation_observations_materialized=False,sampling=SAMPLING,
        max_calls=8,retries=0,completion_with_observations=4096,context=8192,
        transport='scripts/provider_stream.py',reserved_terminal_tokens=96,
        treatment='Public-example self-tracing instruction versus neutral review instruction. Both return a full module under identical schema/source/contract/examples/grader; no helper preservation, tool execution or revision feedback. Self-check behavior is requested, not observed.',
        limitations='One procedural case, four samples per arm. Narrow screen only. No training or Arena wrapper equivalence. Screen alone cannot establish transfer or leaderboard gain.',
        selection='All assigned attempts retained; unknown usage withholds fitness. Candidate proceeds only with no unknown-usage failures, positive full-solve delta, nonnegative native semantic mean delta and no negative per-task full-solve delta. Freeze selection before any fresh confirmation. No retry or redesign on confirmation.')

class Binding:
    def __init__(self,job):
        if job not in schedule('screen'):
            raise ValueError('only exact screen assignments admitted')
        frozen=capture(job['task_id'],job['seed'],job['arm'])
        self.env=DirectRepairEnvironment()
        self.action_type=DirectRepairAction
        obs=self.env.reset(task_id=job['task_id'],seed=job['seed']).model_dump()
        if obs!=json.loads(frozen['messages'][1]['content']):raise ValueError('native reset changed')
        self.messages=frozen['messages'];self.prompt_sha256=frozen['prompt_sha256']
        self.problem_sha256=frozen['problem_sha256']
        self.direct=True
    def parse(self,text):return self.action_type.model_validate_json(text,strict=True)
    def step(self,action):return self.env.step(action).model_dump()
    def diagnose(self,native):
        if native['error'].startswith('Invalid function edit;'):
            return dict(category='edit_rejection',native_reward=native['reward'],semantic_reward=None)
        return classify(SimpleNamespace(_direct=self.env) if self.direct else self.env,native)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    with a.output.open('x') as f:json.dump(bundle(),f,indent=2)
    print(digest(bundle()))
