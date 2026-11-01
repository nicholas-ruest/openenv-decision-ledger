"""Unsealed bridge to the existing amendment-bound accounting and supervisor.

No new reservation implementation, credential source, route or spending cap.
"""
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time
from zoneinfo import ZoneInfo
import finite_qualification as finite
import preserve_first as p


def require_live_ready(*args):
    from case_materializer import verify_case
    import matched_protocol as protocol
    return verify_case(protocol.jobs('screen')[0],*args)


def verify_dependencies():
    pins=json.loads(Path(__file__).with_name('transport-source-pins.json').read_text())
    for name, expected in pins.items():
        if hashlib.sha256((p.ROOT/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('pinned financial/provider/supervisor source changed')


def verify_clean_source(expected):
    if (subprocess.check_output(['git','-C',str(p.ROOT),'rev-parse','HEAD'],text=True).strip()!=expected
        or subprocess.check_output(['git','-C',str(p.ROOT),'status','--porcelain'],text=True).strip()):
        raise ValueError('exact clean immutable source required')


def operating_seconds(now=None):
    local=datetime.now(ZoneInfo('America/Toronto')) if now is None else now
    if local.tzinfo is None:raise ValueError('aware clock required')
    local=local.astimezone(ZoneInfo('America/Toronto'))
    seconds=min(1200,(local.replace(hour=23,minute=0,second=0,microsecond=0)-local).total_seconds())
    if seconds<=0:raise ValueError('fixed23Toronto stop reached')
    return seconds


class ConservativeBackend:
    """Eight original one-action requests inside unchanged larger admission.

    The existing backend requires a 16-request quote. Retain that conservative
    quote (including its 8096 ceiling); actual requests remain at most eight
    and 6000 each. This does not relax the original backend contract.
    """
    scripted=False
    def __init__(self, original):
        self.original=original;self.counter=original.counter
        self.deadline=None;self.labels=set();self.called=set()

    def admit(self,bounds,generation,deadline):
        if bounds!=[28672]*8 or generation!=6000 or deadline<=time.monotonic():
            raise ValueError('exact whole one-action phase quote required')
        if self.deadline is not None:raise ValueError('one original admission only')
        self.original.admit([28672]*16,8096,deadline)
        self.deadline=deadline

    def reserve(self,label,prompt,generation,deadline):
        import matched_protocol as protocol
        if (self.deadline is None or not time.monotonic()<deadline<=self.deadline
            or prompt!=28672 or generation!=6000 or len(self.labels)>=8
            or label in self.labels or label not in {j['attempt_id']+':0' for j in protocol.jobs('screen')}):raise ValueError('original admitted finite request required')
        self.original.reserve(label,prompt,generation,deadline)
        self.labels.add(label)

    def call(self,payload,timeout,job):
        import matched_protocol as protocol
        label=job.get('attempt_id','')+':0'
        if (job not in protocol.jobs('screen') or label not in self.labels
            or label in self.called or self.deadline is None
            or not 0<timeout<=360 or time.monotonic()>=self.deadline
            or payload.get('max_tokens')!=6000
            or {k:v for k,v in payload.items() if k not in ('messages','max_tokens')}!=p.SAMPLING):
            raise ValueError('reserved original screen request only')
        self.called.add(label) # A failed/unknown call cannot be retried/refunded.
        return self.original.call(payload,min(timeout,self.deadline-time.monotonic()),job)

    def check_reply(self,response):return self.original.check_reply(response)
    def check_message(self,message):return self.original.check_message(message)


def guarded_backend(args):
    require_live_ready(getattr(args,'case_audit',None),getattr(args,'case_audit_sha256',None))
    verify_clean_source(args.expected_source);operating_seconds();verify_dependencies()
    module=p.load('preserve_first_existing_financial_backend',
                  'research/software-public-pass-confirmation-20261031/caller.py')
    return ConservativeBackend(module.LiveBackend(args.receipt,args.reconciliation,
                                                 args.tokenizer,args.amendment_sha256))


def _entry(deadline,backend,counter,output):
    _,summary=finite.run(backend,counter,output,deadline)
    return 0 if summary['complete'] else 1


def supervise_qualification(backend,counter,output,seconds,*,now=None):
    if backend.scripted is not True:raise ValueError('scripted qualification only')
    if type(seconds) not in (int,float) or not math.isfinite(seconds) or not 0<seconds<=1200:
        raise ValueError('finite unchanged whole-phase supervisor required')
    seconds=min(seconds,operating_seconds(now))
    output=Path(output);receipt=output.with_suffix('.supervision.jsonl')
    if output.exists() or receipt.exists():raise ValueError('fresh archive and supervision receipt required')
    verify_dependencies()
    supervisor=p.load('preserve_first_existing_supervisor',
                      'integrations/software-repair/scripts/screen_deadline.py')
    result=supervisor.run_bounded(_entry,(backend,counter,output),seconds,receipt)
    return dict(result,scripted=True,live_evidence=False,remote_cancellation_attested=False)
