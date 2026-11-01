"""Atomic finite delegation to unchanged accounting, streaming and supervision."""
import math
from pathlib import Path
import threading
import time
import paired_caller as caller

n=caller.p.n
existing=n.original.load('top_level_existing_guardrails',
    'research/software-preserve-first-action-20261101/guarded_transport.py')


class AtomicDelegation:
    def __init__(self,original):
        self.original=original;self.scripted=original.scripted;self.counter=original.counter
        self.deadline=None;self.labels=set();self.called=set();self.lock=threading.RLock()
        self.phase='qualification' if self.scripted else 'screen'

    def admit(self,bounds,generation,deadline):
        with self.lock:
            if (self.deadline is not None or bounds!=[28672]*8 or generation!=6000
                or not math.isfinite(deadline) or not 0<deadline-time.monotonic()<=1200):
                raise ValueError('one original finite whole-phase admission required')
            # Keep the existing conservative 16-request/8096 ceiling contract.
            self.original.admit([28672]*16,8096,deadline);self.deadline=deadline

    def reserve(self,label,prompt,generation,deadline):
        with self.lock:
            if (self.deadline is None or not time.monotonic()<deadline<=self.deadline
                or prompt!=28672 or generation!=6000 or label in self.labels or len(self.labels)>=8
                or label not in {j['attempt_id']+':0' for j in caller.p.jobs(self.phase)}):
                raise ValueError('unique admitted original request only')
            self.original.reserve(label,prompt,generation,deadline);self.labels.add(label)

    def call(self,payload,timeout,job):
        with self.lock:
            label=job.get('attempt_id','')+':0'
            if (self.deadline is None or time.monotonic()>=self.deadline or job not in caller.p.jobs(self.phase)
                or label not in self.labels or label in self.called or not 0<timeout<=360
                or payload.get('max_tokens')!=6000
                or {k:v for k,v in payload.items() if k not in ('messages','max_tokens')}!=n.original.SAMPLING):
                raise ValueError('one reserved original call required')
            self.called.add(label)
            timeout=min(timeout,self.deadline-time.monotonic())
        # Existing pinned provider_stream creates a fresh AsyncClient per call.
        # HTTP runs outside the bookkeeping lock; failed calls stay consumed.
        return self.original.call(payload,timeout,job)

    def check_reply(self,response):return self.original.check_reply(response)
    def check_message(self,message):return self.original.check_message(message)


def require_live_ready(*args):
    raise ValueError('paired source/case materializer unsealed; no private reads or live backend')


def guarded_backend(args):
    require_live_ready(getattr(args,'case_audit',None),getattr(args,'case_audit_sha256',None))
    existing.verify_clean_source(args.expected_source);existing.operating_seconds();existing.verify_dependencies()
    module=n.original.load('top_level_existing_financial_backend',
        'research/software-public-pass-confirmation-20261031/caller.py')
    return AtomicDelegation(module.LiveBackend(args.receipt,args.reconciliation,args.tokenizer,args.amendment_sha256))


def _entry(deadline,backend,counter,output):
    _,summary=caller.run(backend,counter,output,deadline)
    return 0 if summary['complete'] else 1


def supervise_qualification(backend,counter,output,seconds,*,now=None):
    if backend.scripted is not True:raise ValueError('scripted qualification only')
    if type(seconds) not in (int,float) or not math.isfinite(seconds) or not 0<seconds<=1200:
        raise ValueError('finite unchanged whole-phase wall required')
    seconds=min(seconds,existing.operating_seconds(now))
    output=Path(output);receipt=output.with_suffix('.supervision.jsonl')
    if output.exists() or receipt.exists():raise ValueError('fresh archive and supervisor receipt required')
    existing.verify_dependencies()
    supervisor=n.original.load('top_level_existing_supervisor','integrations/software-repair/scripts/screen_deadline.py')
    result=supervisor.run_bounded(_entry,(backend,counter,output),seconds,receipt)
    return dict(result,scripted=True,live_evidence=False,remote_cancellation_attested=False)
