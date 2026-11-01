"""Immutable private source/case lease; public source refuses before private reads."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import matched_protocol as p

CASE_AUDIT_SHA256=None
_cached=None
METHOD_FILES=tuple('research/software-entry-order-review-20261101/'+n for n in ('order_diagnostic.py','revision_environment.py','matched_protocol.py','finite_caller.py','guarded_transport.py','live_screen.py','assess_screen.py','assess_qualification.mjs'))


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def prior():
    global _cached
    if _cached is None:
        path=p.d.ROOT/'research/software-top-level-note-20261101';sys.path.insert(0,str(path))
        spec=importlib.util.spec_from_file_location('entry_order_prior_case_rules',path/'sealed_case.py')
        _cached=importlib.util.module_from_spec(spec);spec.loader.exec_module(_cached)
    return _cached

def method_hashes():
    old=prior()
    return {n:sha(p.d.ROOT/n) for n in old._prior().METHOD_FILES+old.METHOD_FILES+METHOD_FILES}


def verify_case(job,path,expected):
    if job not in p.jobs('screen'):raise ValueError('screen only; confirmation remains unmaterialized')
    if not isinstance(CASE_AUDIT_SHA256,str) or not re.fullmatch('[a-f0-9]{64}',CASE_AUDIT_SHA256):raise ValueError('source/case lease unsealed; no private reads or new Native input')
    if path is None or expected!=CASE_AUDIT_SHA256 or sha(path)!=expected:raise ValueError('exact private source/case lease required')
    value=json.loads(Path(path).read_text());old=prior();base=old._prior()
    if value.get('kind')!='entry-order-review-case-audit' or value.get('method_sha256')!=method_hashes():raise ValueError('original relation method changed')
    current=value
    anchors=[('top-level-note-case-audit','software_repair-ignore-d3',3200000,old.method_hashes),('preserve-first-case-audit','software_repair-ignore-d3',3180000,base.method_hashes),('failure-advice-case-audit','software_repair-ignore-d2',3160000,None)]
    chain=[]
    for kind,task,seed,hashes in anchors:
        parent_path=Path(current['parent_audit_path'])
        if sha(parent_path)!=current['parent_audit_sha256']:raise ValueError('preceding closed audit changed')
        parent=json.loads(parent_path.read_text())
        if parent.get('kind')!=kind or parent.get('task_id')!=task or parent.get('new_seed')!=seed or (hashes and parent.get('method_sha256')!=hashes()):raise ValueError('latest closed study anchor required')
        required=sorted(parent['prior_task_seed_pairs']+[[task,seed]])
        if current['prior_task_seed_pairs']!=required or current['prior_inventory_sha256']!=p.digest(required):raise ValueError('prior cases dropped or replaced')
        chain.append((parent,dict(task_id=task,seed=seed)));current=parent
    for audit,anchor in reversed(chain):base.verify_inventory(audit,anchor)
    return dict(base.verify_inventory(value,job),case_audit_sha256=expected)


class ScreenTrial(p.Trial):
    def __init__(self,job,path,expected):
        verify_case(job,path,expected)
        from revision_environment import RevisionEnvironment
        class Environment(RevisionEnvironment):
            def reset(self,seed=None,episode_id=None,**kwargs):
                if seed!=job['seed'] or kwargs!={'task_id':job['task_id']}:raise ValueError('original assignment only')
                return self._initialize(seed,episode_id,kwargs)
        p.Trial._initialize(self,job,Environment(arm=job['arm']))


def materialize(job,path=None,expected=None):return ScreenTrial(job,path,expected)

def execution_hashes():return {n:sha(Path(__file__).with_name(n)) for n in ('order_diagnostic.py','revision_environment.py','matched_protocol.py','finite_caller.py','guarded_transport.py','entry_case.py','live_screen.py','assess_screen.py','assess_qualification.mjs')}
