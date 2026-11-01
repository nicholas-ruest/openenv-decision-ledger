"""Native screen construction gated by an immutable private inventory lease."""
import hashlib
import json
from pathlib import Path
import re
import sys
import matched_protocol as protocol
import preserve_first as p

# Never publish a private case seal. No CLI/environment override exists.
CASE_AUDIT_SHA256=None
METHOD_FILES=('scripts/software-helper-policy.py',
 'research/software-preserve-first-action-20261101/preserve_first.py',
 'research/software-preserve-first-action-20261101/matched_protocol.py',
 'research/software-preserve-first-action-20261101/finite_qualification.py',
 'research/software-preserve-first-action-20261101/guarded_transport.py',
 'research/software-preserve-first-action-20261101/assemble_qualification.py',
 'research/software-preserve-first-action-20261101/live_screen.py',
 'research/software-preserve-first-action-20261101/assess_archive.py',
 'research/software-preserve-first-action-20261101/assess_qualification.mjs',
 'research/software-function-trial-20261029/trial.py',
 'research/software-terminal-audit-20261028/terminal_audit.py',
 'integrations/software-repair/repair_env/direct_environment.py',
 'integrations/software-repair/repair_env/tasks.py',
 'integrations/software-repair/repair_env/ignore_repair.py',
 'integrations/software-repair/repair_env/environment.py',
 'integrations/software-repair/repair_env/runner.py')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def method_hashes():return {name:sha(p.ROOT/name) for name in METHOD_FILES}


def verify_inventory(value,job):
    sys.path.insert(0,str(p.ROOT/'integrations/software-repair'))
    from repair_env.tasks import make_task
    from repair_env.direct_environment import DirectRepairEnvironment
    pairs=value['prior_task_seed_pairs']
    if (not pairs or any(type(x) is not list or len(x)!=2 or type(x[0]) is not str or type(x[1]) is not int for x in pairs)
        or pairs!=sorted(pairs) or len({tuple(x) for x in pairs})!=len(pairs)
        or [job['task_id'],job['seed']] in pairs):raise ValueError('complete original distinct inventory required')
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
    return dict(verified=True,input_overlap=0)


def verify_case(job,path,expected):
    if job not in protocol.jobs('screen'):raise ValueError('screen only; confirmation stays unmaterialized')
    if not isinstance(CASE_AUDIT_SHA256,str) or not re.fullmatch('[a-f0-9]{64}',CASE_AUDIT_SHA256):
        raise ValueError('private case/source lease unsealed; no artifact reads or Native construction')
    if path is None or expected!=CASE_AUDIT_SHA256 or sha(path)!=expected:
        raise ValueError('exact source-bound private audit required')
    value=json.loads(Path(path).read_text())
    if value.get('kind')!='preserve-first-case-audit' or value.get('method_sha256')!=method_hashes():
        raise ValueError('frozen helper-guidance method differs')
    parent_path=Path(value['parent_audit_path'])
    if sha(parent_path)!=value['parent_audit_sha256']:raise ValueError('preceding audit differs')
    parent=json.loads(parent_path.read_text())
    # The latest closed advice screen must remain in the complete inventory,
    # including its unfinished called assignment. No older inventory selection.
    anchor=dict(task_id='software_repair-ignore-d2',seed=3160000)
    if (parent.get('kind')!='failure-advice-case-audit' or parent.get('task_id')!=anchor['task_id']
        or parent.get('new_seed')!=anchor['seed']):raise ValueError('latest closed study anchor required')
    verify_inventory(parent,anchor)
    required=sorted(parent['prior_task_seed_pairs']+[[anchor['task_id'],anchor['seed']]])
    if value['prior_task_seed_pairs']!=required or value['prior_inventory_sha256']!=p.digest(required):
        raise ValueError('prior cases dropped or replaced')
    return dict(verify_inventory(value,job),case_audit_sha256=expected)


class ScreenTrial(p.QualificationTrial):
    def __init__(self,job,path,expected):
        verify_case(job,path,expected)
        class Binding(p.QualificationBinding):
            def __init__(self,current):
                if current!=job:raise ValueError('original assignment required')
                self._reset(current['task_id'],current['seed'],current['arm'])
        frozen=Binding(job)
        p.original.Trial.__init__(self,job,frozen.prompt_sha256,frozen.problem_sha256,binding_factory=Binding)


def materialize(job,path=None,expected=None):return ScreenTrial(job,path,expected)


def execution_hashes():
    names=('preserve_first.py','matched_protocol.py','case_materializer.py','finite_qualification.py',
        'assemble_qualification.py','guarded_transport.py','transport-source-pins.json','live_screen.py',
        'assess_archive.py','assess_qualification.mjs')
    return {name:sha(Path(__file__).with_name(name)) for name in names}
