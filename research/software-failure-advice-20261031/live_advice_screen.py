"""Manual bounded screen worker; public source remains unsealed by default."""
import argparse
import fcntl
import json
import os
from pathlib import Path

import failure_protocol as p
import finite_qualification as c
import failure_transport as b
from assemble_archives import assemble_screen


def no_other_workers():
    found=[]
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit() or int(entry.name)==os.getpid():continue
        try:args=(entry/'cmdline').read_bytes().split(b'\0')
        except OSError:continue
        names={Path(x.decode(errors='replace')).name for x in args if x}
        if names&{'caller.py','live_screen.py','live_advice_screen.py','finite_caller.py','repair-signal-screen.py','darwin.sh'}:found.append(int(entry.name))
    if found:raise ValueError('existing caller/Darwin worker; launch refused')


def prior_chunks(args,counter):
    if type(args.chunk) is not int or args.chunk not in range(4) or len(args.prior)!=args.chunk:
        raise ValueError('all original earlier chunks required; no resume/retry/skip')
    if len({x.resolve() for x in args.prior})!=len(args.prior) or args.output.resolve() in {x.resolve() for x in args.prior}:
        raise ValueError('distinct fresh archives required')
    if args.prior:
        for path in args.prior:
            receipt=[json.loads(line) for line in path.with_suffix('.supervision.jsonl').read_text().splitlines()]
            terminal=receipt[-1]
            if (terminal.get('event')!='terminal' or terminal.get('status')!='completed'
                or terminal.get('worker_exitcode')!=0 or not terminal.get('shutdown_verified') or not terminal.get('finished_before_deadline')):
                raise ValueError('prior original worker did not verify completion/shutdown')
        paths=args.prior+[args.output.parent/('unexecuted-'+str(i)) for i in range(args.chunk,4)]
        report=assemble_screen(paths,counter,args.case_audit,args.case_audit_sha256)
        if (report['recorded']!=2*args.chunk or report['independently_replayed']!=2*args.chunk
            or any(r['recorded'] and r['category'] in ('provider','budget','execution') for r in report['rows'])):
            raise ValueError('incomplete/failed prior chunk; phase stays inconclusive')


def execute(deadline,args):
    b.verify_clean_source(args.expected_source);b.operating_seconds();b.verify_dependencies()
    c.require_live_ready(args.case_audit,args.case_audit_sha256)
    base=b.load('failure_advice_prior_counter',p.ROOT/'scripts/repair-signal-screen.py')
    counter=base.helper.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=args.tokenizer,tokenizer_sha256=base.TOKENIZER_SHA))
    prior_chunks(args,counter)
    backend=b.guarded_backend(args)
    c.run_screen_chunk(args.chunk,backend,backend.counter,args.output,deadline,args.case_audit,args.case_audit_sha256)
    return 0


def parser():
    result=argparse.ArgumentParser(allow_abbrev=False,description=__doc__)
    result.add_argument('--execute',action='store_true');result.add_argument('--chunk',type=int)
    result.add_argument('--prior',type=Path,nargs='*',default=[])
    for name in ('receipt','reconciliation','tokenizer','output','case-audit'):result.add_argument('--'+name,type=Path)
    for name in ('expected-source','case-audit-sha256','amendment-sha256'):result.add_argument('--'+name)
    return result


def main():
    args=parser().parse_args()
    if not args.execute:print(json.dumps(p.plan()));return
    if any(v is None for k,v in vars(args).items() if k not in ('execute','prior')):
        raise ValueError('explicit original source/case/audit and fresh archive required')
    seconds=b.require_live_supervision(args.expected_source,args.output,args.case_audit,args.case_audit_sha256)
    no_other_workers();os.umask(0o077)
    # The parent holds this lock until the existing supervisor attests shutdown.
    with open('/home/ruv/arena-inference-study.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        supervisor=b.load('failure_advice_live_supervisor',p.ROOT/'integrations/software-repair/scripts/screen_deadline.py')
        result=supervisor.run_bounded(execute,(args,),seconds,args.output.with_suffix('.supervision.jsonl'))
        print(json.dumps(dict(result,remote_cancellation_attested=False)))


if __name__=='__main__':main()
