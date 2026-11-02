"""Case-bound original backend adapter; no worker entry point or public admission."""
import copy,math,threading,time
from pathlib import Path
import financial_bridge as bridge
if Path(bridge.__file__).resolve()!=Path(__file__).with_name('financial_bridge.py').resolve():
    raise ValueError('exact sibling financial bridge required')


def prepare(args):
    # Original gate precedes private artifacts, credentials and backend construction.
    original,case=bridge.original_backend(args)
    return _AtomicOriginal(original,case)


class _AtomicOriginal:
    scripted=False
    def __init__(self,original,case):
        if original.scripted is not False or case.get('independently_regenerated') is not True:
            raise ValueError('original backend and independently regenerated case required')
        jobs=copy.deepcopy(case['jobs'])
        if len(jobs)!=8 or len({bridge.gate.digest(j) for j in jobs})!=8:
            raise ValueError('all eight distinct original assignments required')
        self.jobs={j['attempt_id']:bridge.gate.digest(j) for j in jobs}
        if len(self.jobs)!=8:raise ValueError('original unique attempt identities required')
        self.original=original;self.counter=original.counter;self.deadline=None
        self.lock=threading.RLock();self.reserved={};self.reservation_attempted=set();self.called=set();self.returned=set();self.active=set()

    def admit(self,bounds,generation,deadline):
        with self.lock:
            bridge.gate.operating_seconds()
            if (self.deadline is not None or bounds!=[28672]*16 or generation!=8096
                or type(deadline) not in (int,float) or not math.isfinite(deadline)
                or not 0<deadline-time.monotonic()<=1200):
                raise ValueError('one original whole-phase deadline and admission required')
            value=bridge.preflight_complete_plan(self.original,deadline)
            self.deadline=deadline
            return value

    def reserve(self,label,prompt,generation,deadline):
        with self.lock:
            bridge.gate.operating_seconds()
            stem,turn=label.rsplit(':',1)
            if (self.deadline is None or stem not in self.jobs or turn not in ('0','1')
                or label in self.reservation_attempted or len(self.reservation_attempted)>=16 or prompt!=28672
                or not time.monotonic()<deadline<=self.deadline
                or type(generation) is not int or not 0<generation<=8096
                or (turn=='0' and generation!=6000)
                or (turn=='1' and stem+':0' not in self.returned)
                or any(x.startswith(stem+':') for x in self.active)):
                raise ValueError('original sequential one-time reservation required')
            # A reservation may have committed before an error. Never retry or refund it.
            self.reservation_attempted.add(label)
            self.original.reserve(label,prompt,generation,deadline)
            self.reserved[label]=generation

    def call(self,payload,timeout,job,turn):
        with self.lock:
            bridge.gate.operating_seconds()
            label=job.get('attempt_id','')+':'+str(turn)
            if (type(turn) is not int or turn not in (0,1)
                or self.jobs.get(job.get('attempt_id'))!=bridge.gate.digest(job)
                or label not in self.reserved or label in self.called or len(self.active)>=2
                or self.deadline is None or time.monotonic()>=self.deadline
                or type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<timeout<=360
                or type(payload.get('max_tokens')) is not int or payload['max_tokens']!=self.reserved[label]
                or {k:v for k,v in payload.items() if k not in ('messages','max_tokens')}!=bridge.gate.SAMPLING):
                raise ValueError('exact original reserved request required')
            self.called.add(label);self.active.add(label)
            timeout=min(timeout,self.deadline-time.monotonic())
        try:
            # Pinned LiveBackend.call has no turn parameter. Do not alter the backend.
            response=self.original.call(payload,timeout,job)
            with self.lock:self.returned.add(label)
            return response
        finally:
            with self.lock:self.active.remove(label)

    def check_reply(self,response):return self.original.check_reply(response)
    def check_message(self,message):return self.original.check_message(message)
