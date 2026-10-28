"""Two bounded trusted processes: phase worker, then independent verifier.

No provider driver, admission or automatic resume. Both entrypoints and their
immutable dependencies must be independently reviewed/pinned by the caller.
"""
import copy
import hashlib
import math
import os
from pathlib import Path
import sys
import time

from training.lifecycle import bounded_worker
from durable_phase import durable_new
from media_protocol import digest
from verified_phase import schedule
from accounting_archive import validate_config, _read


def pinned(path,sha):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=sha:
        raise ValueError('pinned regular entrypoint required')
    return path.resolve()


def supervise_accounted(root,worker,worker_sha,verifier,verifier_sha,plan,phase,expected_config,*,deadline,now=time.monotonic):
    """Verifier CLI: PHASE_ROOT EXPECTED_CONFIG PROOF_PATH.

    A trusted verifier must run accounting_archive.verify_archive using the
    external config, pinned counter, ledger and bounded replay. It must write
    its returned object to PROOF_PATH exclusively and durably. A generic exit0
    or the generation-only supervisor's verification is never enough.
    """
    current=now()
    if type(current) not in (int,float) or type(deadline) not in (int,float) or not math.isfinite(current) or not math.isfinite(deadline) or not 0<deadline-current<=1800:
        raise ValueError('finite shared deadline within1800seconds required')
    schedule(plan,phase);config=copy.deepcopy(expected_config);validate_config(config)
    worker=pinned(worker,worker_sha);verifier=pinned(verifier,verifier_sha)
    root=Path(root).resolve();root.mkdir(mode=0o700,exist_ok=False)
    fd=os.open(root.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
    durable_new(root,'expected-accounting.json',config)
    durable_new(root,'supervisor-claim.json',{'worker_sha256':worker_sha,'verifier_sha256':verifier_sha,
        'plan_sha256':digest(plan),'phase':phase,'accounting_sha256':digest(config),'resume_authorized':False})
    def run(args):
        remaining=deadline-now()
        if remaining<=0:return {'status':'deadline','returncode':None}
        return bounded_worker([sys.executable,*map(str,args)],cwd=root,seconds=remaining,grace=.2)
    execution=run([worker,root/'phase']);verification=None;proof=None;status=execution['status']
    if status=='completed':
        try:
            # The worker cannot choose or edit the external expected contract,
            # or pre-seed a proof and skip its independent verification process.
            if _read(root,'expected-accounting.json')!=config or (root/'verification.json').exists() or (root/'verification.json').is_symlink():
                raise ValueError('worker altered verifier inputs')
            pinned(verifier,verifier_sha)
            verification=run([verifier,root/'phase',root/'expected-accounting.json',root/'verification.json'])
            if verification['status']!='completed':status='verification_'+verification['status']
            else:
                proof=_read(root,'verification.json')
                if proof['accounting_sha256']!=digest(config) or proof['episodes_recomputed']!=16 or proof['execution_authorized'] is not False or proof['arena_wrapper_equivalent'] is not False:
                    raise ValueError('incomplete independent verification proof')
                complete=_read(root/'phase','complete.json')
                if proof['report']!=complete or complete['complete'] is not True or complete['attempts']!=16:
                    raise ValueError('independent phase assessment mismatch')
                if now()>=deadline:raise TimeoutError('verification deadline reached')
                status='completed'
        except Exception as exc:
            status='invalid_accounted_archive';proof=None
            durable_new(root,'verification-error.json',{'exception_type':type(exc).__name__})
    report={'status':status,'worker_status':execution['status'],
        'verifier_status':verification['status'] if verification else None,
        'archive_verified':status=='completed' and proof is not None,
        'accounting_sha256':digest(config),'verification_sha256':digest(proof) if status=='completed' and proof else None,
        'arena_wrapper_equivalent':False,'provider_billing_stopped':None,'resume_authorized':False,
        'scope':'trusted pinned entrypoints and dependencies; inherited process groups only'}
    durable_new(root,'supervisor-result.json',report)
    return report
