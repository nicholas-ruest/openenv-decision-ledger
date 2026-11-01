"""Manual single-supervisor screen. Default prints a plan; public lease unsealed."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import time
import guarded_transport as bridge
import finite_qualification as finite
import matched_protocol as protocol
from assemble_qualification import assemble_screen


def no_other_workers():
    found=[]
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit() or int(entry.name)==os.getpid():continue
        try:args=(entry/'cmdline').read_bytes().split(b'\0')
        except OSError:continue
        names={Path(x.decode(errors='replace')).name for x in args if x}
        if names&{'caller.py','live_screen.py','live_advice_screen.py','finite_caller.py','repair-signal-screen.py','darwin.sh'}:
            found.append(int(entry.name))
    if found:raise ValueError('existing inference worker; no duplicate launch')


def execute_phase(deadline,args):
    bridge.verify_clean_source(args.expected_source)
    backend=bridge.guarded_backend(args)
    finite.run_screen(backend,backend.counter,args.output,deadline,args.case_audit,args.case_audit_sha256)
    report=assemble_screen(args.output,backend.counter,args.case_audit,args.case_audit_sha256)
    with (args.output/'phase-evidence.json').open('x') as stream:json.dump(report,stream,indent=2)
    return 0 if report['complete'] and time.monotonic()<deadline else 1


def require_supervision(args):
    bridge.require_live_ready(args.case_audit,args.case_audit_sha256)
    bridge.verify_clean_source(args.expected_source);bridge.verify_dependencies()
    seconds=bridge.operating_seconds()
    if args.output.exists() or args.output.with_suffix('.supervision.jsonl').exists():
        raise ValueError('fresh original archive and supervisor receipt required')
    return seconds


def main():
    parser=argparse.ArgumentParser(allow_abbrev=False,description=__doc__)
    parser.add_argument('--execute',action='store_true')
    for key in ('receipt','reconciliation','tokenizer','output','case-audit'):parser.add_argument('--'+key,type=Path)
    for key in ('expected-source','case-audit-sha256','amendment-sha256'):parser.add_argument('--'+key)
    args=parser.parse_args()
    if not args.execute:print(json.dumps(protocol.plan()));return
    if any(v is None for k,v in vars(args).items() if k!='execute'):
        raise ValueError('explicit source/case/audit and fresh archive required')
    seconds=require_supervision(args);no_other_workers();os.umask(0o077)
    with open('/home/ruv/arena-inference-study.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        supervisor=bridge.p.load('preserve_first_live_supervisor','integrations/software-repair/scripts/screen_deadline.py')
        result=supervisor.run_bounded(execute_phase,(args,),seconds,args.output.with_suffix('.supervision.jsonl'))
        print(json.dumps(dict(result,remote_cancellation_attested=False)))


if __name__=='__main__':main()
