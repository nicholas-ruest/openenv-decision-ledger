"""Qualification-only atomic delegation and unchanged fixed-stop supervision."""
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import threading
import time
import finite_caller as c


def require_live_ready(path=None,expected=None):
    from entry_case import verify_case
    return verify_case(c.p.jobs('screen')[0],path,expected)


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def verify_clean_source(expected):
    import subprocess
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.p.d.ROOT,text=True).strip()!=expected or subprocess.check_output(['git','status','--porcelain'],cwd=c.p.d.ROOT,text=True).strip():raise ValueError('exact clean immutable source required')


def verify_dependencies():
    pins=json.loads((c.p.d.ROOT/'research/software-preserve-first-action-20261101/transport-source-pins.json').read_text())
    for name,value in pins.items():
        if hashlib.sha256((c.p.d.ROOT/name).read_bytes()).hexdigest()!=value:raise ValueError('pinned financial/provider/supervisor source changed')


def guarded_backend(args):
    require_live_ready(getattr(args,'case_audit',None),getattr(args,'case_audit_sha256',None))
    verify_clean_source(args.expected_source);verify_dependencies();operating_seconds()
    module=load('entry_order_original_financial_backend',c.p.d.ROOT/'research/software-public-pass-confirmation-20261031/caller.py')
    original=module.LiveBackend(args.receipt,args.reconciliation,args.tokenizer,args.amendment_sha256)
    return AtomicDelegation(original,case_audit=args.case_audit,case_audit_sha256=args.case_audit_sha256)


class AtomicDelegation:
    def __init__(self,original,*,case_audit=None,case_audit_sha256=None):
        if original.scripted is not True:require_live_ready(case_audit,case_audit_sha256)
        self.phase='qualification' if original.scripted is True else 'screen'
        self.original=original;self.scripted=original.scripted;self.counter=original.counter;self.deadline=None
        self.lock=threading.RLock();self.reserved={};self.called=set();self.returned=set();self.active=set()

    def admit(self,bounds,generation,deadline):
        with self.lock:
            if self.deadline is not None or bounds!=[28672]*16 or generation!=8096 or not math.isfinite(deadline) or not 0<deadline-time.monotonic()<=1200:raise ValueError('one original conservative whole-phase admission required')
            self.original.admit(bounds,generation,deadline);self.deadline=deadline

    def reserve(self,label,prompt,generation,deadline):
        with self.lock:
            valid={j['attempt_id']+':'+str(t) for j in c.p.jobs(self.phase) for t in (0,1)}
            stem,turn=label.rsplit(':',1)
            if (self.deadline is None or label not in valid or label in self.reserved or len(self.reserved)>=16 or prompt!=28672
                or not time.monotonic()<deadline<=self.deadline or type(generation) is not int or not 0<generation<=8096
                or (turn=='0' and generation!=6000) or (turn=='1' and stem+':0' not in self.returned)
                or any(x.startswith(stem+':') for x in self.active)):raise ValueError('one sequential original reservation required')
            self.original.reserve(label,prompt,generation,deadline);self.reserved[label]=generation

    def call(self,payload,timeout,job,turn):
        label=job.get('attempt_id','')+':'+str(turn)
        with self.lock:
            if (job not in c.p.jobs(self.phase) or turn not in (0,1) or label not in self.reserved or label in self.called
                or len(self.active)>=2 or self.deadline is None or time.monotonic()>=self.deadline
                or not 0<timeout<=360 or payload.get('max_tokens')!=self.reserved[label]
                or {k:v for k,v in payload.items() if k not in ('messages','max_tokens')}!=c.p.SAMPLING):raise ValueError('original reserved one-call authorization required')
            self.called.add(label);self.active.add(label);timeout=min(timeout,self.deadline-time.monotonic())
        try:
            result=self.original.call(payload,timeout,job,turn) if self.scripted else self.original.call(payload,timeout,job)
            with self.lock:self.returned.add(label)
            return result
        finally:
            with self.lock:self.active.remove(label)

    def check_reply(self,response):return self.original.check_reply(response)
    def check_message(self,message):return self.original.check_message(message)


def operating_seconds(now=None):
    local=datetime.now(ZoneInfo('America/Toronto')) if now is None else now
    if local.tzinfo is None:raise ValueError('aware clock required')
    local=local.astimezone(ZoneInfo('America/Toronto'))
    seconds=min(1200,(local.replace(hour=23,minute=0,second=0,microsecond=0)-local).total_seconds())
    if seconds<=0:raise ValueError('fixed23Toronto stop reached')
    return seconds


def _entry(deadline,backend,counter,output):
    _,summary=c.run(backend,counter,output,deadline)
    return 0 if summary['complete'] else 1


def supervise_qualification(backend,counter,output,seconds):
    if backend.scripted is not True or type(seconds) not in (int,float) or not math.isfinite(seconds) or not 0<seconds<=1200:raise ValueError('finite scripted supervision required')
    seconds=min(seconds,operating_seconds());output=Path(output);receipt=output.with_suffix('.supervision.jsonl')
    if output.exists() or receipt.exists():raise ValueError('fresh archive and supervisor receipt required')
    source=c.p.d.ROOT/'integrations/software-repair/scripts/screen_deadline.py'
    if hashlib.sha256(source.read_bytes()).hexdigest()!='08950e6ff362572f34c4fa2397de80c97dbf15d0380c04c5398be12e6abc9977':raise ValueError('pinned supervisor source changed')
    spec=importlib.util.spec_from_file_location('entry_order_original_supervisor',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return dict(module.run_bounded(_entry,(backend,counter,output),seconds,receipt),scripted=True,live_evidence=False,remote_cancellation_attested=False)
