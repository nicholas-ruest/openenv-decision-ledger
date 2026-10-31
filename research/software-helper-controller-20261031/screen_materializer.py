"""Helper-specific Native screen materialization behind an immutable case lease.

Case provenance is not financial admission. Confirmation remains blocked until
a helper-specific positive-screen artifact gate exists. No provider API here.
"""
import copy
import hashlib
import json
from pathlib import Path
import re

import matched_protocol as p

PARENT_AUDIT_SHA256='8345b5cade73758e36bc164800ab650025cd165ef02a6113604cb13231fa9e5a'
METHOD_FILES=('research/software-helper-controller-20261031/helper_policy.py',
    'research/software-helper-controller-20261031/matched_protocol.py',
    'research/software-action-example-20261030/action_example_protocol.py',
    'research/software-action-example-20261030/action_example_environment.py',
    'integrations/software-repair/repair_env/tasks.py',
    'integrations/software-repair/repair_env/ignore_repair.py')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def method_hashes():return {name:sha(p.ROOT/name) for name in METHOD_FILES}


def execution_hashes():
    names=('helper_policy.py','matched_protocol.py','screen_materializer.py','finite_caller.py',
        'replay_matched.py','assemble_phase.py','assess_qualification.mjs','transport_bridge.py',
        'transport-source-pins.json','live_screen.py')
    return {name:sha(Path(__file__).with_name(name)) for name in names}


def verify_case_contents(value,job):
    """Independently regenerate the exact input inventory, never trust flags."""
    from repair_env.tasks import make_task
    from repair_env.direct_environment import DirectRepairEnvironment
    pairs=value['prior_task_seed_pairs']
    if (not pairs or pairs!=sorted(pairs) or len({tuple(x) for x in pairs})!=len(pairs)
            or any(type(x) is not list or len(x)!=2 or type(x[0]) is not str or type(x[1]) is not int for x in pairs)
            or [job['task_id'],job['seed']] in pairs):
        raise ValueError('original complete distinct prior inventory required')
    past=set()
    for task,seed in pairs:
        t=make_task(task,seed);past.update(p.digest(c.args) for c in t.public+t.hidden)
    t=make_task(job['task_id'],job['seed']);current={p.digest(c.args) for c in t.public+t.hidden}
    obs=DirectRepairEnvironment().reset(task_id=t.task_id,seed=t.seed)
    if (value['task_id']!=job['task_id'] or value['new_seed']!=job['seed']
            or value['prior_case_count']!=len(pairs) or value['prior_input_count']!=len(past)
            or value['new_input_count']!=len(current) or past&current
            or value['prior_input_set_sha256']!=p.digest(sorted(past))
            or value['new_input_set_sha256']!=p.digest(sorted(current))
            or value['new_source_examples_sha256']!=p.digest(dict(source=obs.source,examples=obs.examples))):
        raise ValueError('regenerated Native case inventory differs or overlaps')
    return dict(verified=True,prior_cases=len(pairs),prior_inputs=len(past),new_inputs=len(current),input_overlap=0)


def verify_live_case(job,path,expected):
    if job not in p.jobs('screen'):
        raise ValueError('screen only; confirmation requires an independently selected helper screen')
    from finite_caller import LIVE_CASE_AUDIT_SHA256
    if not isinstance(LIVE_CASE_AUDIT_SHA256,str) or not re.fullmatch('[a-f0-9]{64}',LIVE_CASE_AUDIT_SHA256):
        raise ValueError('unsealed live case inventory; Native construction refused')
    if path is None or expected!=LIVE_CASE_AUDIT_SHA256 or sha(path)!=expected:
        raise ValueError('exact source-bound case lease required')
    value=json.loads(Path(path).read_text())
    if value.get('kind')!='helper-controller-case-audit' or value.get('method_sha256')!=method_hashes():
        raise ValueError('frozen helper/Native method differs')
    parent_path=Path(value['parent_audit_path'])
    if value['parent_audit_sha256']!=PARENT_AUDIT_SHA256 or sha(parent_path)!=PARENT_AUDIT_SHA256:
        raise ValueError('exact last independently audited case inventory required')
    parent=json.loads(parent_path.read_text())
    required=sorted(parent['prior_task_seed_pairs']+[[p.TASK,parent['new_seed']]])
    if (parent['new_seed']!=3130000 or value['prior_task_seed_pairs']!=required
            or len(required)<48 or value['prior_inventory_sha256']!=p.digest(required)):
        raise ValueError('prior inventory dropped, reset or silently replaced')
    return dict(verify_case_contents(value,job),case_audit_sha256=expected)


def construct_existing_trial(job):
    """Shared Native construction; direct controls use only existing3100000."""
    from action_example_protocol import Trial as OriginalTrial
    from action_example_environment import ActionExampleEnvironment,ProposalAction
    from terminal_audit import classify
    from helper_policy import HelperPreservationPolicy
    base=object.__new__(OriginalTrial)
    base.action_type=ProposalAction;base.classify=classify;base.job=copy.deepcopy(job)
    base.env=ActionExampleEnvironment(arm='schema_only')
    reset=base.env.reset(task_id=job['task_id'],seed=job['seed']).model_dump()
    base.messages=[dict(role='system',content='Return exactly one JSON action instance matching this schema. '
        'No markdown, diff, or tool command. '+p.canonical(ProposalAction.model_json_schema())),
        dict(role='user',content=p.canonical(reset))]
    base.turn=0;base.closed=False;base.native=[]
    return HelperPreservationPolicy(base,arm=job['arm'])


class ScreenTrial:
    def __init__(self,job,case_audit,case_sha256):
        self.case_proof=verify_live_case(job,case_audit,case_sha256)
        self.policy=construct_existing_trial(job)
    @property
    def messages(self):return copy.deepcopy(self.policy.trial.messages)
    def consume(self,text):return self.policy.consume_model(text,finish_reason='stop')
