"""Manual source-sealed helper screen. Default plan cannot construct a backend.

This delegates the existing amendment-bound financial backend and existing Linux
supervisor. Confirmation is deliberately absent, including any promotion API.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import time

import matched_protocol as p
import finite_caller as caller
import transport_bridge as bridge
from assemble_phase import assemble_screen


def no_other_workers():
    found=[]
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit() or int(entry.name)==os.getpid():continue
        try:args=(entry/'cmdline').read_bytes().split(b'\0')
        except (OSError,ProcessLookupError):continue
        names={Path(a.decode(errors='replace')).name for a in args if a}
        if names&{'caller.py','live_screen.py','finite_caller.py','darwin.sh'}:
            found.append(int(entry.name))
    if found:raise ValueError('existing caller/Darwin worker; launch refused')


def prior_chunks(args):
    if type(args.chunk) is not int or args.chunk not in range(4) or len(args.prior)!=args.chunk:
        raise ValueError('all exact earlier chunks required; no resume, retry or skip')
    if len(set(map(str,args.prior)))!=len(args.prior) or args.output in args.prior:
        raise ValueError('distinct original archives required')
    if args.prior:
        # Missing future paths preserve all eight assigned outcomes while only
        # independently validating the prefix. They are never executed here.
        paths=args.prior+[args.output.parent/('unexecuted-'+str(i)) for i in range(args.chunk,4)]
        a=assemble_screen(paths,args.counter,args.case_audit,args.case_audit_sha256)
        if (a['recorded']!=2*args.chunk or a['independently_replayed']!=2*args.chunk
                or any(r['recorded'] and r['category'] in ('provider','budget','execution') for r in a['rows'])):
            raise ValueError('earlier chunk incomplete or failed; phase is inconclusive')


def execute(deadline,args):
    bridge.verify_clean_source(args.expected_source)
    bridge.operating_seconds()
    caller.require_live_ready(args.case_audit,args.case_audit_sha256)
    bridge.verify_dependencies()
    # Tokenizer-only loading allows prior replay before constructing a backend.
    base=bridge.load('helper_prior_counter',p.ROOT/'scripts/repair-signal-screen.py')
    args.counter=base.helper.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=args.tokenizer,tokenizer_sha256=base.TOKENIZER_SHA))
    prior_chunks(args)
    backend=bridge.guarded_backend(args)
    caller.screen_chunk(args.chunk,backend,backend.counter,args.output,deadline,args.case_audit,args.case_audit_sha256)
    return 0


def parser():
    value=argparse.ArgumentParser(allow_abbrev=False,description=__doc__)
    value.add_argument('--execute',action='store_true')
    value.add_argument('--chunk',type=int)
    value.add_argument('--prior',type=Path,nargs='*',default=[])
    for name in ('receipt','reconciliation','tokenizer','output','case-audit'):
        value.add_argument('--'+name,type=Path)
    for name in ('expected-source','case-audit-sha256','amendment-sha256'):
        value.add_argument('--'+name)
    return value


def main():
    args=parser().parse_args()
    if not args.execute:
        print(json.dumps(p.plan()));return
    if any(v is None for k,v in vars(args).items() if k not in ('execute','prior')):
        raise ValueError('explicit immutable source/case and fresh financial audit required')
    # The default source returns here, before file inspection or credentials.
    caller.require_live_ready(args.case_audit,args.case_audit_sha256)
    bridge.verify_clean_source(args.expected_source)
    seconds=bridge.operating_seconds();bridge.verify_dependencies()
    if args.output.exists() or args.output.with_suffix('.supervision.jsonl').exists():
        raise ValueError('fresh archive and supervision receipt required')
    no_other_workers()
    os.umask(0o077)
    # One host-wide helper study at a time. Keep the lock in the parent until
    # the existing supervisor has attested worker shutdown.
    with open('/home/ruv/arena-helper-study.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        supervisor=bridge.load('helper_live_supervisor',p.ROOT/'integrations/software-repair/scripts/screen_deadline.py')
        result=supervisor.run_bounded(execute,(args,),seconds,args.output.with_suffix('.supervision.jsonl'))
        print(json.dumps(dict(result,remote_cancellation_attested=False)))


if __name__=='__main__':main()
