"""Manual single-supervisor screen; public source/case seal is unset."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import time
import finite_caller as c
import guarded_transport as b


def no_other_workers():
    for d in Path('/proc').iterdir():
        if not d.name.isdigit() or int(d.name)==os.getpid():continue
        try:args=(d/'cmdline').read_bytes().split(b'\0')
        except OSError:continue
        if {Path(x.decode(errors='replace')).name for x in args if x}&{'caller.py','live_pairs.py','live_screen.py','live_advice_screen.py','finite_caller.py','darwin.sh','same-prompt-screen.py'}:raise ValueError('existing inference worker; no duplicate launch')


def require_supervision(args):
    b.require_live_ready(args.case_audit,args.case_audit_sha256);b.verify_clean_source(args.expected_source);b.verify_dependencies()
    if args.output.exists() or args.output.with_suffix('.supervision.jsonl').exists():raise ValueError('fresh archive and supervisor receipt required')
    return b.operating_seconds()


def execute_phase(deadline,args):
    b.verify_clean_source(args.expected_source);backend=b.guarded_backend(args)
    _,summary=c.run_screen(backend,backend.counter,args.output,deadline,args.case_audit,args.case_audit_sha256)
    report=c.assemble(args.output,backend.counter,'screen',args.case_audit,args.case_audit_sha256)
    c.write(args.output/'phase-evidence.json',report)
    c.write(args.output/'supervision-binding.json',dict(worker_pid=os.getpid(),parent_pid=os.getppid(),deadline=deadline,source=args.expected_source,case_audit_sha256=args.case_audit_sha256,archive=str(args.output.resolve())))
    return 0 if summary['complete'] and report['complete'] and time.monotonic()<deadline else 1


def main():
    parser=argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--execute',action='store_true')
    for k in ('receipt','reconciliation','tokenizer','output','case-audit'):parser.add_argument('--'+k,type=Path)
    for k in ('expected-source','case-audit-sha256','amendment-sha256'):parser.add_argument('--'+k)
    args=parser.parse_args()
    if not args.execute:print(json.dumps(c.p.plan()));return
    if any(v is None for k,v in vars(args).items() if k!='execute'):raise ValueError('explicit original execution inputs required')
    seconds=require_supervision(args);no_other_workers();os.umask(0o077)
    with open('/home/ruv/arena-inference-study.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        supervisor=b.load('entry_order_live_supervisor',c.p.d.ROOT/'integrations/software-repair/scripts/screen_deadline.py')
        print(json.dumps(dict(supervisor.run_bounded(execute_phase,(args,),seconds,args.output.with_suffix('.supervision.jsonl')),remote_cancellation_attested=False)))


if __name__=='__main__':main()
