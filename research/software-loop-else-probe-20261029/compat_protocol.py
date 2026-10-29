"""Eight-call disjoint model probe for standard loop-else compatibility."""
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
ARMS=('function_block_available',)
NAMESPACE='loop-else-confirm-20261029'
SEEDS={'screen':(2540000,2540100),'confirmation':(2550000,2550100)}
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
    value=original.capture(task,seed,arm)
    value['request']=dict(copy.deepcopy(SAMPLING),messages=value['messages'])
    return value

def bundle():
    groups=[]
    for index,task in enumerate(TARGETS):
        seed=SEEDS['screen'][index]
        arms={arm:capture(task,seed,arm) for arm in ARMS}
        if len(arms)!=1:
            raise ValueError('problem differs across arms')
        groups.append(dict(task_id=task,seed=seed,
            problem_sha256=arms[ARMS[0]]['problem_sha256'],arms=arms))
    return dict(namespace=NAMESPACE,screen_jobs=schedule('screen'),
        confirmation_jobs=schedule('confirmation'),screen_groups=groups,
        confirmation_observations_materialized=False,sampling=SAMPLING,
        max_calls=8,retries=0,completion_with_observations=4096,context=8192,
        transport='scripts/provider_stream.py',reserved_terminal_tokens=96,
        treatment='Eight fresh function-interface replies, each subsequently scored unchanged by both pinned runtimes. Only standard loop-else acceptance differs. No comparison between helper interfaces; no self-check prompt or revision feedback.',
        limitations='Two procedural cases, four samples per case/arm. No training or Arena wrapper equivalence. Screen alone cannot establish transfer or leaderboard gain.',
        selection='This is disjoint confirmation of a runtime compatibility fix selected from earlier posthoc diagnosis. Retain eight assigned attempts; compare the same unmodified reply under old and candidate runtimes. Unknown usage or incomplete assignments withhold confirmation. Report paired full/partial/failure changes with four-sample MetaHarness groups; no training or ranking claim.')

class Binding:
    def __init__(self,job):
        if job not in schedule('screen'):
            raise ValueError('only exact screen assignments admitted')
        frozen=capture(job['task_id'],job['seed'],job['arm'])
        self.env=DirectRepairEnvironment() if job['arm']=='full_module' else FunctionEditEnvironment()
        self.action_type=DirectRepairAction if job['arm']=='full_module' else FunctionEditAction
        obs=self.env.reset(task_id=job['task_id'],seed=job['seed']).model_dump()
        if obs!=json.loads(frozen['messages'][1]['content']):raise ValueError('native reset changed')
        self.messages=frozen['messages'];self.prompt_sha256=frozen['prompt_sha256']
        self.problem_sha256=frozen['problem_sha256']
        self.direct=job['arm']=='full_module'
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
