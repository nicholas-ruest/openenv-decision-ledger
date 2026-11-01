"""Source-bound private case lease. Public source refuses before artifact reads."""
import hashlib
import json
from pathlib import Path
import re
import matched_note as p

n=p.n
prior=None

def _prior():
    global prior
    if prior is None:
        prior=n.original.load('top_level_prior_inventory_rules',
            'research/software-preserve-first-action-20261101/case_materializer.py')
    return prior
CASE_AUDIT_SHA256=None
METHOD_FILES=tuple('research/software-top-level-note-20261101/'+name for name in (
    'top_level_note.py','matched_note.py','paired_caller.py','paired_transport.py',
    'live_pairs.py','assess_pairs.py','assess_qualification.mjs'))


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def method_hashes():return {name:sha(n.ROOT/name) for name in _prior().METHOD_FILES+METHOD_FILES}


def verify_case(job,path,expected):
    if job not in p.jobs('screen'):raise ValueError('screen only; confirmation remains unmaterialized')
    if not isinstance(CASE_AUDIT_SHA256,str) or not re.fullmatch('[a-f0-9]{64}',CASE_AUDIT_SHA256):
        raise ValueError('private source/case lease unsealed; no private reads or new Native input')
    if path is None or expected!=CASE_AUDIT_SHA256 or sha(path)!=expected:
        raise ValueError('exact immutable private case lease required')
    prior=_prior()
    value=json.loads(Path(path).read_text())
    if value.get('kind')!='top-level-note-case-audit' or value.get('method_sha256')!=method_hashes():
        raise ValueError('original syntax-note method differs')
    parent_path=Path(value['parent_audit_path'])
    if sha(parent_path)!=value['parent_audit_sha256']:raise ValueError('latest closed helper audit changed')
    parent=json.loads(parent_path.read_text())
    anchor=dict(task_id='software_repair-ignore-d3',seed=3180000)
    if (parent.get('kind')!='preserve-first-case-audit' or parent.get('task_id')!=anchor['task_id']
        or parent.get('new_seed')!=anchor['seed'] or parent.get('method_sha256')!=prior.method_hashes()):
        raise ValueError('exact latest closed helper study anchor required')
    older_path=Path(parent['parent_audit_path'])
    if sha(older_path)!=parent['parent_audit_sha256']:raise ValueError('preceding advice audit changed')
    older=json.loads(older_path.read_text());advice=dict(task_id='software_repair-ignore-d2',seed=3160000)
    if (older.get('kind')!='failure-advice-case-audit' or older.get('task_id')!=advice['task_id']
        or older.get('new_seed')!=advice['seed']):raise ValueError('preceding closed advice anchor required')
    prior.verify_inventory(older,advice)
    required_parent=sorted(older['prior_task_seed_pairs']+[[advice['task_id'],advice['seed']]])
    if parent['prior_task_seed_pairs']!=required_parent or parent['prior_inventory_sha256']!=n.original.digest(required_parent):
        raise ValueError('closed advice inventory was dropped or replaced')
    prior.verify_inventory(parent,anchor)
    required=sorted(parent['prior_task_seed_pairs']+[[anchor['task_id'],anchor['seed']]])
    if value['prior_task_seed_pairs']!=required or value['prior_inventory_sha256']!=n.original.digest(required):
        raise ValueError('closed helper inventory was dropped or replaced')
    return dict(prior.verify_inventory(value,job),case_audit_sha256=expected)


class ScreenTrial(n.QualificationTrial):
    def __init__(self,job,path,expected):
        verify_case(job,path,expected)
        class Binding(n.Binding):
            def __init__(self,current):
                if current!=job:raise ValueError('original source-bound screen assignment required')
                self._reset(current['task_id'],current['seed'],'baseline')
                if current['arm']=='top_level_only':
                    observation=json.loads(self.messages[1]['content']);observation['prompt']+=n.NOTE
                    self.messages[1]['content']=n.original.canonical(observation)
                self.prompt_sha256=n.original.digest(self.messages)
        frozen=Binding(job)
        n.original.original.Trial.__init__(self,job,frozen.prompt_sha256,frozen.problem_sha256,binding_factory=Binding)


def materialize(job,path=None,expected=None):return ScreenTrial(job,path,expected)


def execution_hashes():
    return {name:sha(Path(__file__).with_name(name)) for name in (
        'top_level_note.py','matched_note.py','paired_caller.py','paired_transport.py',
        'sealed_case.py','live_pairs.py','assess_pairs.py','assess_qualification.mjs')}
