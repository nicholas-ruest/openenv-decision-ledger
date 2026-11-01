"""Native case materialization behind an unsealed immutable private audit lease."""
import copy
import hashlib
import json
from pathlib import Path
import re
import failure_protocol as p
from failure_advice import FailureAdviceTrial

# Public source never carries a private audit hash. A separately qualified
# private immutable execution revision is required; no CLI/env override exists.
CASE_AUDIT_SHA256=None
METHOD_FILES=('research/software-failure-advice-20261031/failure_advice.py',
 'research/software-failure-advice-20261031/failure_protocol.py',
 'research/software-action-example-20261030/action_example_protocol.py',
 'research/software-action-example-20261030/action_example_environment.py',
 'integrations/software-repair/repair_env/tasks.py',
 'integrations/software-repair/repair_env/ignore_repair.py')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def method_hashes():return {name:sha(p.ROOT/name) for name in METHOD_FILES}


def verify_inventory(value,job):
    from repair_env.tasks import make_task
    from repair_env.direct_environment import DirectRepairEnvironment
    pairs=value['prior_task_seed_pairs']
    if (not pairs or any(type(x) is not list or len(x)!=2 or type(x[0]) is not str or type(x[1]) is not int for x in pairs)
        or pairs!=sorted(pairs) or len({tuple(x) for x in pairs})!=len(pairs)
        or [job['task_id'],job['seed']] in pairs):raise ValueError('original distinct complete inventory required')
    past=set()
    for task,seed in pairs:
        task=make_task(task,seed);past.update(p.digest(c.args) for c in task.public+task.hidden)
    task=make_task(job['task_id'],job['seed']);current={p.digest(c.args) for c in task.public+task.hidden}
    obs=DirectRepairEnvironment().reset(task_id=task.task_id,seed=task.seed)
    if (past&current or value['task_id']!=job['task_id'] or value['new_seed']!=job['seed']
        or value['prior_case_count']!=len(pairs) or value['prior_input_count']!=len(past)
        or value['new_input_count']!=len(current) or value['prior_input_set_sha256']!=p.digest(sorted(past))
        or value['new_input_set_sha256']!=p.digest(sorted(current))
        or value['new_source_examples_sha256']!=p.digest(dict(source=obs.source,examples=obs.examples))):
        raise ValueError('independently regenerated inventory differs or overlaps')
    return dict(verified=True,input_overlap=0,prior_cases=len(pairs),new_inputs=len(current))


def verify_case(job,path,expected):
    if job not in p.jobs('screen'):raise ValueError('screen only; confirmation requires a separately selected positive screen')
    if not isinstance(CASE_AUDIT_SHA256,str) or not re.fullmatch('[a-f0-9]{64}',CASE_AUDIT_SHA256):
        raise ValueError('private case/source lease unsealed; no artifact reads or Native construction')
    if path is None or expected!=CASE_AUDIT_SHA256 or sha(path)!=expected:raise ValueError('exact source-bound private artifact required')
    value=json.loads(Path(path).read_text())
    if value.get('kind')!='failure-advice-case-audit' or value.get('method_sha256')!=method_hashes():raise ValueError('frozen method differs')
    parent_path=Path(value['parent_audit_path'])
    if sha(parent_path)!=value['parent_audit_sha256']:raise ValueError('parent audit differs')
    parent=json.loads(parent_path.read_text())
    # Anchor to the preceding closed helper screen, not a selectable older audit.
    if parent['task_id']!=p.TASK or parent['new_seed']!=3140000:raise ValueError('preceding complete study inventory required')
    verify_inventory(parent,dict(task_id=p.TASK,seed=3140000))
    required=sorted(parent['prior_task_seed_pairs']+[[p.TASK,3140000]])
    if value['prior_task_seed_pairs']!=required or value['prior_inventory_sha256']!=p.digest(required):raise ValueError('prior cases were dropped or replaced')
    return dict(verify_inventory(value,job),case_audit_sha256=expected)


def construct_existing(job):
    from action_example_protocol import Trial
    from action_example_environment import ActionExampleEnvironment,ProposalAction
    from terminal_audit import classify
    base=object.__new__(Trial);base.action_type=ProposalAction;base.classify=classify;base.job=copy.deepcopy(job)
    base.env=ActionExampleEnvironment(arm='schema_only')
    reset=base.env.reset(task_id=job['task_id'],seed=job['seed']).model_dump()
    base.messages=[dict(role='system',content='Return exactly one JSON action instance matching this schema. No markdown, diff, or tool command. '+p.canonical(ProposalAction.model_json_schema())),dict(role='user',content=p.canonical(reset))]
    base.turn=0;base.closed=False;base.native=[]
    return FailureAdviceTrial(base,arm=job['arm'])


def materialize(job,path=None,expected=None):
    verify_case(job,path,expected)
    return construct_existing(job)
