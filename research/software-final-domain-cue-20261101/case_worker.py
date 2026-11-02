"""Prepared original-backend worker entry; public worker/case seals stay closed."""
import importlib.util,json,math,os
from pathlib import Path
import live_gate as gate
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('case_worker_original_supervision',HERE/'qualification_supervisor.py')
support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)


def require_worker(args):
    # No argument access, private reads, Native or credentials before immutable seals.
    if not all(gate.sealed(x) for x in (gate.CASE_AUDIT_SHA256,gate.LATEST_CLOSED_AUDIT_SHA256,gate.WORKER_QUALIFICATION_SHA256)):
        raise ValueError('worker/source/case qualification unsealed; no execution')
    if args.phase!='screen':raise ValueError('confirmation remains closed')
    gate.source_guard(args.expected_source);gate.operating_seconds()
    if args.worker_qualification_sha256!=gate.WORKER_QUALIFICATION_SHA256 or gate.sha(args.worker_qualification)!=gate.WORKER_QUALIFICATION_SHA256:
        raise ValueError('exact worker qualification receipt required')
    value=json.loads(Path(args.worker_qualification).read_text())
    if (value.get('kind')!='case_bound_original_worker_qualification'
        or value.get('method_sha256')!=gate.method_hashes()
        or value.get('original_supervisor_sha256')!=support.PIN
        or value.get('scripted_supervisor_binding_verified') is not True
        or value.get('independent_parent_raw_replay_verified') is not True
        or value.get('native_and_tokenizer_initialized_after_fork') is not True
        or value.get('actual_backend_constructed') is not False
        or value.get('synthetic_provider_only') is not True
        or any(type(value.get(k)) is not int or value[k]!=v for k,v in
               [('assigned',8),('synthetic_calls',16),('unknown_usage_calls',0),('max_inflight',2),('max_reserving',1)])):
        raise ValueError('qualified exact worker methods and original supervision required')
    return value


def components():
    import case_caller as c
    if Path(c.__file__).resolve()!=HERE/'case_caller.py':raise ValueError('exact prepared caller required')
    return c


def worker_entry(deadline,args,parent_pid):
    require_worker(args);startup=support.require_fresh_parent()
    if os.getppid()!=parent_pid:raise ValueError('original supervisor parent required')
    startup.update(worker_pid=os.getpid(),parent_pid=parent_pid,deadline=deadline,
        source=args.expected_source,mode='guarded_original_backend_worker')
    support.write(args.output.with_suffix('.worker-startup.json'),startup)
    c=components()
    # The unchanged constructor independently checks case/root/credit/parents/ledgers.
    # Tokenizer and environment-only credentials are accessed only in this child.
    backend=c.transport.prepare(args)
    rows,summary,report=c.phase(args,backend,args.output,deadline)
    support.write(args.output/'phase-evidence.json',report)
    support.write(args.output/'worker-binding.json',dict(worker_pid=os.getpid(),parent_pid=parent_pid,
        deadline=deadline,source=args.expected_source,mode='guarded_original_backend_worker',
        archive=str(args.output.resolve()),counter_initialized_in_worker=True,
        phase_complete=summary['complete'],selection_passed=False,model_improvement=False))
    return 0 if summary['complete'] else 1


def supervise(args):
    require_worker(args);state=support.require_fresh_parent()
    seconds=gate.operating_seconds()
    if not math.isfinite(seconds) or not 0<seconds<=1200:raise ValueError('original operating window required')
    for path in (args.output,args.output.with_suffix('.supervision.jsonl'),args.output.with_suffix('.launch.json'),args.output.with_suffix('.worker-startup.json')):
        if path.exists():raise ValueError('fresh archive and original supervisor receipt required')
    support.write(args.output.with_suffix('.launch.json'),dict(parent_pid=os.getpid(),parent_state=state,
        source=args.expected_source,archive=str(args.output.resolve()),mode='guarded_original_backend_worker'))
    result=support.supervisor().run_bounded(worker_entry,(args,os.getpid()),seconds,args.output.with_suffix('.supervision.jsonl'))
    # Raw supervisor completion confers no selection, provenance or performance credit.
    return dict(supervisor=result,selection_passed=False,model_improvement=False,
                independent_post_run_audit_required=True)
