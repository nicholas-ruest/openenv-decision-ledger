"""Local media phase process-group supervision. No provider/submission driver."""
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

from training.lifecycle import bounded_worker
from durable_phase import durable_new
from media_durable import inspect_saved, schedule
from media_protocol import digest
from trajectory_audit import assess_phase


def verify_saved_phase(root, plan, phase):
    """Read-only consistency check; native replay occurred inside the worker.

    Does not authenticate provider evidence or re-run any action after deadline.
    """
    inspected=inspect_saved(root)
    claim=inspected['claim']
    if claim['plan_sha256']!=digest(plan) or claim['phase']!=phase or claim['jobs']!=[list(j) for j in schedule(plan,phase)]:
        raise ValueError('frozen child claim mismatch')
    files=sorted(root.glob('*-episode.json'))
    if len(files)!=16:raise ValueError('complete16 episode records required')
    rows=[]
    for file in files:
        obj=json.loads(file.read_text());row=obj['validated'];raw=obj['payload']
        if row['raw_sha256']!=digest(raw):raise ValueError('raw/validated binding mismatch')
        rows.append(row)
    expected={**assess_phase(rows,plan,phase),'complete':True,'is_training':False,'promotion':False}
    if json.loads((root/'complete.json').read_text())!=expected:
        raise ValueError('complete report differs from assessed saved episodes')
    return expected


def supervise(root, script, script_sha256, plan, phase, *, deadline, now=time.monotonic):
    """Execute one pinned trusted script; pass only its fresh phase directory.

    Worker dependencies must also be immutable/attested externally. The script
    must retain the inherited session/process group; escaping descendants are
    outside this local cleanup contract. No retry/resume is authorized.
    """
    current=now()
    if type(deadline) not in (int,float) or type(current) not in (int,float) or not math.isfinite(deadline) or not math.isfinite(current) or not 0<deadline-current<=1800:
        raise ValueError('finite remaining deadline within1800seconds required')
    schedule(plan,phase)
    script=Path(script)
    if script.is_symlink() or not script.is_file() or hashlib.sha256(script.read_bytes()).hexdigest()!=script_sha256:
        raise ValueError('pinned regular worker source required')
    root=Path(root);root.mkdir(mode=0o700,exist_ok=False)
    fd=os.open(root.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
    durable_new(root,'supervisor-claim.json',{'script_sha256':script_sha256,'plan_sha256':digest(plan),'phase':phase,'resume_authorized':False})
    remaining=deadline-now()
    if not math.isfinite(remaining) or remaining<=0:
        durable_new(root,'supervisor-result.json',{'status':'deadline_before_launch','provider_billing_stopped':None,'resume_authorized':False})
        return {'status':'deadline_before_launch','provider_billing_stopped':None,'resume_authorized':False}
    # Reuse the existing TERM/KILL process-group implementation. No stdout,
    # stderr, process environment or credential values are logged.
    process=bounded_worker([sys.executable,str(script.resolve()),str((root/'phase').resolve())],cwd=root.resolve(),seconds=remaining,grace=.2)
    status=process['status'];verification=None
    if status=='completed':
        try:
            verification=verify_saved_phase(root/'phase',plan,phase)
        except Exception as exc:
            status='invalid_archive'
            durable_new(root,'verification-error.json',{'exception_type':type(exc).__name__})
    report={'status':status,'process_status':process['status'],'returncode':process['returncode'],
            'elapsed_seconds':process['elapsed_seconds'],'archive_verified':verification is not None,
            'provider_billing_stopped':None,'resume_authorized':False,
            'scope':'local inherited process group only; no escaped-session or remote billing claim'}
    durable_new(root,'supervisor-result.json',report)
    return report
