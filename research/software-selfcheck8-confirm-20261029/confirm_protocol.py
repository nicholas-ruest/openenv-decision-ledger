"""Disjoint confirmation of a frozen positive self-tracing prompt screen."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research/software-selfcheck8-20261029'))
import selfcheck_protocol as original
from repair_env.direct_environment import DirectRepairEnvironment,DirectRepairAction

digest=original.digest
canonical=original.canonical
ARMS=original.ARMS

def selection(value):
    if (value.get('screen_source')!='730102d5753eff01003cde189d9f42c2b648f00a'
            or value.get('screen_inputs_sha256')!='669253433c09c02f9e74ebe4b3ef6322df53d6da2b3cdf344e0c0a589d80344a'
            or value.get('screen_selection_passed') is not True
            or value.get('assigned')!=8 or value.get('observed_calls')!=8
            or value.get('unknown_usage')!=0 or not value.get('full_rate_delta',0)>0
            or not value.get('semantic_mean_delta',-1)>=0
            or len(value.get('response_ids',[]))!=8
            or len(set(value['response_ids']))!=8):
        raise ValueError('frozen complete positive screen selection required')
    for key in ['screen_problem_sha256','screen_assessment_sha256','screen_raw_events_sha256']:
        if len(value.get(key,''))!=64 or any(c not in '0123456789abcdef' for c in value[key]):raise ValueError('bound screen evidence required')
    return value

def bundle(chosen):
    chosen=selection(chosen)
    task='software_repair-ignore-d3';seed=2570000
    arms={arm:original.capture(task,seed,arm) for arm in ARMS}
    if arms[ARMS[0]]['problem']!=arms[ARMS[1]]['problem']:raise ValueError('paired problem differs')
    problem=arms[ARMS[0]]['problem_sha256']
    if problem==chosen['screen_problem_sha256']:raise ValueError('procedural case collision; no replacement seed or redraw')
    jobs=original.schedule('confirmation')
    return dict(namespace=original.NAMESPACE,confirmation_jobs=jobs,
        confirmation_groups=[dict(task_id=task,seed=seed,problem_sha256=problem,arms=arms)],
        screen_selection=chosen,selection_sha256=digest(chosen),sampling=original.SAMPLING,
        max_calls=8,retries=0,completion_with_observations=4096,context=8192,
        treatment='Exact unchanged self-tracing versus neutral review instruction; source/contract/schema/resource/route unchanged from screen. No computed feedback or helper preservation.',
        model_training=False,leaderboard_gain=False,promotion=False)

class Binding(original.Binding):
    def __init__(self,job):
        if job not in original.schedule('confirmation'):raise ValueError('exact disjoint confirmation assignment required')
        frozen=original.capture(job['task_id'],job['seed'],job['arm'])
        self.env=DirectRepairEnvironment();self.action_type=DirectRepairAction
        obs=self.env.reset(task_id=job['task_id'],seed=job['seed']).model_dump()
        if obs!=json.loads(frozen['messages'][1]['content']):raise ValueError('native reset changed')
        self.messages=frozen['messages'];self.prompt_sha256=frozen['prompt_sha256']
        self.problem_sha256=frozen['problem_sha256'];self.direct=True

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--selection',type=Path,required=True);p.add_argument('--selection-sha256',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    raw=a.selection.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=a.selection_sha256:raise ValueError('immutable selection receipt changed')
    value=bundle(json.loads(raw))
    with a.output.open('x') as f:json.dump(value,f,indent=2)
    print(digest(value))
