"""Manual original screen under one supervisor and lock; public seal is unset."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import time
import paired_caller as c
import paired_transport as bridge


def no_other_workers():
    found=[]
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit() or int(entry.name)==os.getpid():continue
        try:args=(entry/'cmdline').read_bytes().split(b'\0')
        except OSError:continue
        names={Path(x.decode(errors='replace')).name for x in args if x}
        if names&{'caller.py','live_pairs.py','live_screen.py','live_advice_screen.py','finite_caller.py',
                  'paired_caller.py','repair-signal-screen.py','same-prompt-screen.py','darwin.sh'}:
            found.append(int(entry.name))
    if found:raise ValueError('existing inference worker; no duplicate launch')


def require_supervision(args):
    bridge.require_live_ready(args.case_audit,args.case_audit_sha256)
    bridge.existing.verify_clean_source(args.expected_source);bridge.existing.verify_dependencies()
    seconds=bridge.existing.operating_seconds()
    if args.output.exists() or args.output.with_suffix('.supervision.jsonl').exists():
        raise ValueError('fresh original archive/supervisor receipt required')
    return seconds


def execute_phase(deadline,args):
    bridge.existing.verify_clean_source(args.expected_source)
    backend=bridge.guarded_backend(args)
    _,summary=c.run_screen(backend,backend.counter,args.output,deadline,args.case_audit,args.case_audit_sha256)
    report=c.assemble(args.output,backend.counter,'screen',args.case_audit,args.case_audit_sha256)
    c.write(args.output/'phase-evidence.json',report)
    return 0 if summary['complete'] and report['complete'] and time.monotonic()<deadline else 1


def main():
    parser=argparse.ArgumentParser(allow_abbrev=False,description=__doc__)
    parser.add_argument('--execute',action='store_true')
    for name in ('receipt','reconciliation','tokenizer','output','case-audit'):
        parser.add_argument('--'+name,type=Path)
    for name in ('expected-source','case-audit-sha256','amendment-sha256'):
        parser.add_argument('--'+name)
    args=parser.parse_args()
    if not args.execute:print(json.dumps(c.plan()));return
    if any(v is None for k,v in vars(args).items() if k!='execute'):
        raise ValueError('explicit source, private case/audit, existing allocation and fresh archive required')
    seconds=require_supervision(args);no_other_workers();os.umask(0o077)
    with open('/home/ruv/arena-inference-study.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        supervisor=bridge.n.original.load('top_level_live_supervisor','integrations/software-repair/scripts/screen_deadline.py')
        result=supervisor.run_bounded(execute_phase,(args,),seconds,args.output.with_suffix('.supervision.jsonl'))
        print(json.dumps(dict(result,remote_cancellation_attested=False)))


if __name__=='__main__':main()
