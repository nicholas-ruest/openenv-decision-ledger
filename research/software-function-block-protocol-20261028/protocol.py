"""Freeze a separate one-response action-affordance comparison; no inference driver."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'research/software-function-edit-20261028'),str(ROOT/'integrations/software-repair')]
from function_edit import FunctionEditEnvironment,FunctionEditAction,TARGETS
from repair_env.direct_environment import DirectRepairEnvironment,DirectRepairAction

ARMS=('full_module','function_block_available')
SEEDS={'screen':(2420000,2420100),'confirmation':(2430000,2430100)}
SAMPLING=dict(model='Qwen/Qwen3.8-27B:deepinfra',temperature=0.7,max_tokens=2048,
              response_format={'type':'json_object'},chat_template_kwargs={'enable_thinking':True})

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
def digest(x):return hashlib.sha256(canonical(x).encode()).hexdigest()

def schedule(phase,namespace):
    if phase not in SEEDS or not namespace or len(namespace)>60 or not all(c.isalnum() or c in '-_' for c in namespace):raise ValueError('explicit phase and archive namespace required')
    rows=[]
    for sample in range(4):
        for task in TARGETS:
            for seed in SEEDS[phase]:
                for arm in ARMS if sample%2==0 else reversed(ARMS):
                    identity=dict(namespace=namespace,phase=phase,sample=sample,task_id=task,seed=seed,arm=arm)
                    rows.append(dict(identity,attempt_id=digest(identity)))
    assert len(rows)==32 and len({r['attempt_id'] for r in rows})==32
    return rows

def capture(task,seed,arm):
    if arm not in ARMS:raise ValueError('declared comparison arm required')
    env=DirectRepairEnvironment() if arm=='full_module' else FunctionEditEnvironment()
    action=DirectRepairAction if arm=='full_module' else FunctionEditAction
    obs=env.reset(task_id=task,seed=seed).model_dump()
    marker='\nRepair the supplied source. Reply once' if arm=='full_module' else '\nReply once with a JSON action.'
    if marker not in obs['prompt']:raise ValueError('frozen instruction boundary changed')
    problem=copy.deepcopy(obs);problem['prompt']=problem['prompt'].split(marker)[0]
    schema=action.model_json_schema()
    messages=[dict(role='system',content='Return exactly one JSON action instance matching this schema. No markdown, diff or tool command. '+canonical(schema)),dict(role='user',content=canonical(obs))]
    return dict(problem=problem,problem_sha256=digest(problem),schema=schema,messages=messages,
                prompt_sha256=digest(messages),request=dict(copy.deepcopy(SAMPLING),messages=messages))

def freeze(output,namespace):
    output.mkdir(exist_ok=False);screen=schedule('screen',namespace);confirmation=schedule('confirmation',namespace)
    groups=[]
    for task in TARGETS:
        for seed in SEEDS['screen']:
            arms={a:capture(task,seed,a) for a in ARMS}
            if arms[ARMS[0]]['problem']!=arms[ARMS[1]]['problem']:raise ValueError('treatment changed problem or supplied source/examples')
            if arms[ARMS[0]]['prompt_sha256']==arms[ARMS[1]]['prompt_sha256']:raise ValueError('expected action-interface treatment absent')
            groups.append(dict(task_id=task,seed=seed,problem_sha256=arms[ARMS[0]]['problem_sha256'],arms=arms))
    value=dict(status='offline_not_admitted',source_candidate='2c7d88fbb35d52d4d1f2311bda27aa829b832389',namespace=namespace,
        screen_jobs=screen,confirmation_jobs=confirmation,screen_groups=groups,
        sampling=SAMPLING,thinking_requested=True,thinking_attested=False,provider_identities_attested=False,
        max_model_calls_per_attempt=1,max_model_calls_per_phase=32,max_retries=0,
        completion_tokens_including_postreset_observations=4096,context_tokens=8192,
        confirmation_observations_materialized=False,paid_execution_authorized=False,new_model_calls=0,
        treatment='Action instructions and schema differ; task contract, source, examples and resource limits match. Function mode may add new helpers and retains full-module fallback. Not an identical-prompt comparison.',
        analysis='Keep all 32 assigned attempts in denominator; format/edit-rejection/execution/provider/budget failures separate from valid wrong/partial/full. Report selected mode without selecting successes. Compare per task and paired seed group; four samples are not four procedural cases.',
        confirmation='Fresh disjoint generation identities and unmaterialized seeds; freeze selection before confirmation. No private transfer or ranking claim without Arena evaluation.',
        unresolved='External account/receipt reconciliation, complete-phase admission, source/provider/transport pins, independent call IDs, hard deadlines and verified actual token costs are still required. No implicit approval from this bundle.')
    (output/'inputs.json').write_text(json.dumps(value,indent=2)+'\n')
    summary=dict(assigned_screen_attempts=32,assigned_confirmation_attempts=32,paired_screen_groups=4,
        procedural_screen_seeds=2,matched_problem_hashes=True,confirmation_observations_materialized=False,
        inputs_sha256=digest(value),new_model_calls=0,paid_execution_authorized=False)
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--namespace',required=True)
    a=p.parse_args();print(json.dumps(freeze(a.output,a.namespace)))
