"""Concrete software revision trial inputs. No provider, billing or submission driver."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/p) for p in ('research/software-revision-candidate-20261028',
    'research/software-public-check-20261028','integrations/software-repair')]
from revision_environment import RevisionEnvironment,RevisionAction,RevisionObservation
from pydantic import ValidationError


def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
def digest(x):return hashlib.sha256(canonical(x).encode()).hexdigest()
def plan():return json.loads((ROOT/'research/software-public-check-20261028/revision-plan.json').read_text())


def jobs(phase,namespace):
    p=plan()
    if phase not in p['seeds'] or not namespace or len(namespace)>60 or not all(c.isalnum() or c in '-_' for c in namespace):
        raise ValueError('explicit phase and fresh archive namespace required')
    rows=[]
    for sample in range(p['samples_per_arm_task_seed']):
        for task in p['tasks']:
            for seed in p['seeds'][phase]:
                # Alternate order within every case. Independent calls must still be made.
                arms=p['arms'] if sample%2==0 else list(reversed(p['arms']))
                for arm in arms:
                    identity=dict(namespace=namespace,phase=phase,task_id=task,seed=seed,sample=sample,arm=arm)
                    rows.append(dict(**identity,attempt_id=digest(identity)))
    if len(rows)!=32 or len({r['attempt_id'] for r in rows})!=32:raise ValueError('frozen complete phase required')
    return rows


class FormatFailure(ValueError):pass


class Trial:
    """A fresh native environment per assigned attempt; no code substitution or redraw.

    Caller must enforce whole-phase admission, durable provider identities, token
    accounting and hard process deadlines before any real call. This class grants
    none of those and contains no network/provider implementation.
    """
    def __init__(self,job):
        self.job=copy.deepcopy(job);self.env=RevisionEnvironment(arm=job['arm'])
        reset=self.env.reset(task_id=job['task_id'],seed=job['seed']).model_dump()
        schema=RevisionAction.model_json_schema()
        self.messages=[dict(role='system',content='Return exactly one JSON action instance matching this schema. No markdown, diff, or tool command. '+canonical(schema)),dict(role='user',content=canonical(reset))]
        self.first_messages_sha256=digest(self.messages)
        self.turn=0;self.closed=False;self.native=[]

    def consume(self,reply):
        if self.closed or self.turn>=2:raise ValueError('attempt already terminal; no retry/redraw')
        self.turn+=1
        try:
            if type(reply) is not str:raise FormatFailure('raw assistant text required')
            action=RevisionAction.model_validate_json(reply,strict=True)
        except (ValidationError,FormatFailure):
            self.closed=True
            return dict(category='format',stage=self.turn,done=True,native_reward=None)
        native=self.env.step(action).model_dump();self.native.append(native)
        self.messages += [dict(role='assistant',content=reply),dict(role='user',content=canonical(native))]
        if native['done']:
            self.closed=True;r=native['reward']
            category=('execution' if native['error'] else 'full' if r==1 else 'partial' if 0<r<1 else 'wrong')
            return dict(category=category,stage=self.turn,done=True,native_reward=r)
        if self.turn!=1 or native['stage']!='revision' or native['remaining_responses']!=1 or native['reward']!=0:
            self.closed=True;raise ValueError('native intermediate contract mismatch')
        return dict(category='awaiting_revision',stage=1,done=False,native_reward=0)


def freeze(output,namespace):
    output.mkdir(exist_ok=False)
    screen=jobs('screen',namespace);confirmation=jobs('confirmation',namespace)
    groups={}
    for job in screen:
        trial=Trial(job);key=job['task_id']+'|'+str(job['seed'])
        if key in groups and groups[key]['messages']!=trial.messages:raise ValueError('first-prompt arm/sample contamination')
        groups[key]=dict(messages=trial.messages,first_messages_sha256=trial.first_messages_sha256)
    # Confirmation identities are committed, but confirmation observations are NOT materialized.
    value=dict(plan_sha256=digest(plan()),namespace=namespace,screen_jobs=screen,confirmation_jobs=confirmation,
               screen_groups=groups,confirmation_observations_materialized=False,
               paid_execution_authorized=False,new_model_calls=0,provider_identities_attested=False,
               native_transport='direct environment model observations, not production Arena chat wrapper')
    (output/'inputs.json').write_text(json.dumps(value,indent=2)+'\n')
    report=dict(screen_attempts=len(screen),confirmation_attempts=len(confirmation),unique_screen_prompts=len(groups),
                inputs_sha256=digest(value),confirmation_observations_materialized=False,new_model_calls=0)
    (output/'summary.json').write_text(json.dumps(report,indent=2)+'\n');return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--namespace',required=True)
    a=p.parse_args();print(json.dumps(freeze(a.output,a.namespace)))
