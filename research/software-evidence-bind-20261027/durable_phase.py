"""Offline-tested coordinator/archive/assessor composition; no provider driver.

A True admission flag is a dependency supplied by the existing whole-phase gate;
it is NOT budget authorization or reconciliation. No CLI executes paid calls.
"""
import json
import math
import os
from pathlib import Path
import tempfile
from raw_evidence import bind,digest


def durable_new(root,name,value):
    """Commit one immutable JSON object; link is exclusive, never replaces a file."""
    if Path(name).name != name:
        raise ValueError('basename required')
    payload=(json.dumps(value,sort_keys=True,allow_nan=False)+'\n').encode()
    fd,path=tempfile.mkstemp(prefix='.pending-',dir=root)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(payload);f.flush();os.fsync(f.fileno())
        os.link(path,root/name)  # atomic publication, fails if target already exists
        directory=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:
        os.unlink(path)


def load_saved(root):
    """Read-only integrity check, never authorizes resuming a partial archive."""
    claim=json.loads((root/'claim.json').read_text())
    saved=[]
    for path in sorted(root.glob('*-result.json')):
        row=json.loads(path.read_text())
        if digest(row['payload'])!=row['payload_sha256']:
            raise ValueError('saved result checksum mismatch')
        saved.append(row['payload'])
    return claim,saved


def run_phase(root,manifest,protocol,prefix,worker,coordinator,assessor,
              reservation_rows,capture,replay,classify,deadline,admitted,now):
    """One fresh bounded phase. worker returns {raw, normalized, fatal_guard_failure}.

    Uses real existing schedule/coordinate, raw binder and paired assessor. Tests
    supply offline workers. Production model dispatch/accounting remain external.
    A saved worker exception has no fabricated response, reward or reservation.
    """
    if admitted is not True:
        raise ValueError('external whole-phase admission required')
    current=now()
    if type(deadline) not in (int,float) or not math.isfinite(deadline) or not math.isfinite(current) or deadline-current>1800:
        raise ValueError('finite wall deadline within1800seconds required')
    assessor.sha(protocol['settings_sha256'])
    phase=manifest['phase']
    if phase not in assessor.SEEDS or tuple(manifest['arms'])!=assessor.ARMS:
        raise ValueError('frozen paired phase required')
    if protocol['runtime_source']!=assessor.RUNTIME:
        raise ValueError('frozen runtime required')
    jobs=coordinator.schedule(assessor.TASKS,assessor.SEEDS[phase])
    if len(jobs)!=32 or len(set(jobs))!=32 or not isinstance(prefix,str) or not 1<=len(prefix)<=80 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in prefix):
        raise ValueError('complete32unique phase and explicit namespace required')
    root=Path(root);root.mkdir(mode=0o700,exist_ok=False)
    parent=os.open(root.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(parent)
    finally:os.close(parent)
    # The root remains claimed even when this write or a later write fails.
    durable_new(root,'claim.json',{'manifest':manifest,'protocol':protocol,'jobs':jobs,'prefix':prefix})
    envelopes=[];records=[];response_ids=set()
    def label(job):return prefix+':'+':'.join(map(str,job))+':0'
    def invoke(job,wall_deadline):
        seq=len(envelopes)
        durable_new(root,f'{seq:04d}-intent.json',{'job':job,'planned_call_label':label(job)})
        try:
            return worker(job,wall_deadline,label(job))
        except BaseException as exc:
            # Persist only exception type, never arbitrary text or credential data.
            durable_new(root,f'{seq:04d}-worker-error.json',{'job':job,'exception_type':type(exc).__name__})
            raise
    def save(job,result):
        seq=len(envelopes)
        payload={'job':job,'result':result}
        durable_new(root,f'{seq:04d}-result.json',{'payload':payload,'payload_sha256':digest(payload)})
        arm,task,seed,sample=job
        envelope={'arm':arm,'task_id':task,'seed':seed,'sample':sample,
                  'planned_call_label':label(job),'raw':result['raw']}
        record=result['normalized']
        # Validate each result before another worker, including native replay.
        bind([envelope],[record],reservation_rows(),protocol['runtime_source'],
             protocol['settings_sha256'],capture,replay,classify)
        response=record.get('provider_response_id_sha256')
        if response is not None:
            if response in response_ids:raise ValueError('response replay across jobs')
            response_ids.add(response)
        envelopes.append(envelope);records.append(record)
    try:
        expected_groups={(t,s) for t in assessor.TASKS for s in assessor.SEEDS[phase]}
        groups=manifest['groups']
        if len(groups)!=4 or {(g['task_id'],g['seed']) for g in groups}!=expected_groups:
            raise ValueError('complete frozen manifest required before work')
        prompts=set();cases={}
        for g in groups:
            case=assessor.sha(g['case_sha256'])
            if g['seed'] in cases and cases[g['seed']]!=case:raise ValueError('procedural case mismatch')
            cases[g['seed']]=case
            if set(g['arms'])!=set(assessor.ARMS):raise ValueError('both manifest arms required')
            for arm in assessor.ARMS:
                prompt=assessor.sha(g['arms'][arm]['prompt_sha256'])
                if prompt in prompts:raise ValueError('distinct arm/group prompts required')
                prompts.add(prompt)
                snapshot=capture(arm,g['task_id'],g['seed'])
                expected={**{k:g[k] for k in ('case_sha256','workspace_sha256')},**g['arms'][arm]}
                for k in ('case_sha256','workspace_sha256','reset_sha256','prompt_sha256'):
                    if snapshot[k]!=expected[k]:raise ValueError('fresh preflight capture differs from manifest')
                if digest(snapshot['files'])!=snapshot['workspace_sha256'] or digest(snapshot['reset'])!=snapshot['reset_sha256'] or digest(snapshot['messages'])!=snapshot['prompt_sha256']:
                    raise ValueError('fresh capture content/hash mismatch')
        if len(set(cases.values()))!=2:raise ValueError('distinct procedural cases required')
        status=coordinator.coordinate(jobs,invoke,save,deadline,admitted,now=now)
        if not status['complete']:
            durable_new(root,'incomplete.json',{'reason':status['reason'],'saved_validated':len(envelopes)})
            return {'complete':False,'reason':status['reason'],'saved_validated':len(envelopes)}
        attestation=bind(envelopes,records,reservation_rows(),protocol['runtime_source'],
                         protocol['settings_sha256'],capture,replay,classify)
        assessment=assessor.assess(manifest,records,protocol['runtime_source'],protocol['settings_sha256'])
        report={'complete':True,'attestation':attestation,'assessment':assessment,
                'manifest_sha256':digest(manifest),'protocol_sha256':digest(protocol),
                'is_training':False,'promotion':False}
        durable_new(root,'complete.json',report)
        return report
    except BaseException as exc:
        durable_new(root,'aborted.json',{'exception_type':type(exc).__name__,
                                       'saved_validated':len(envelopes),'resume_authorized':False})
        raise
