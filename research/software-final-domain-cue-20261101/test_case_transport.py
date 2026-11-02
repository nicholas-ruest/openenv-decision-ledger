"""Synthetic transport only; never construct a real credential-bearing backend."""
import ast,copy,json,threading,time,unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import case_transport as c


class Original:
    scripted=False
    counter=object()
    def __init__(self):self.reserved=[];self.calls=[];self.fail=False;self.enter=threading.Barrier(3);self.release=threading.Event()
    def reserve(self,*args):self.reserved.append(args)
    def call(self,payload,timeout,job):
        self.calls.append(job)
        if self.fail:raise TimeoutError('synthetic unknown reply')
        return {'id':'synthetic'}
    def check_reply(self,response):return 'checked reply'
    def check_message(self,message):return 'checked message'


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.jobs=c.bridge.gate.jobs_for({'task_id':'software_repair-ignore-d3','new_seed':2560000})
        self.original=Original();self.backend=c._AtomicOriginal(self.original,dict(jobs=self.jobs,independently_regenerated=True))
        self.preflight=patch.object(c.bridge,'preflight_complete_plan',return_value={'admitted':True});self.quote=self.preflight.start();self.addCleanup(self.preflight.stop)
        self.clock=patch.object(c.bridge.gate,'operating_seconds',return_value=1200);self.clock.start();self.addCleanup(self.clock.stop)
        self.deadline=time.monotonic()+1100

    def admit(self):self.backend.admit([28672]*16,8096,self.deadline)
    def reserve(self,index=0,turn=0):
        job=self.jobs[index];self.backend.reserve(job['attempt_id']+':'+str(turn),28672,6000 if turn==0 else 1000,self.deadline);return job
    def payload(self,n=6000):return dict(copy.deepcopy(c.bridge.gate.SAMPLING),messages=[],max_tokens=n)

    def test_unsealed_public_source_refuses_before_original_constructor(self):
        with patch.object(c.bridge,'load',side_effect=AssertionError('provider constructor')):
            with self.assertRaisesRegex(ValueError,'unsealed'):c.prepare(None)

    def test_original_signature_exact_call_and_duplicate_refusal(self):
        c.bridge.verify_pins()
        tree=ast.parse((c.bridge.ROOT/'research/software-public-pass-confirmation-20261031/caller.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='LiveBackend')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='call')
        self.assertEqual([a.arg for a in method.args.args],['self','payload','timeout','job'])
        self.admit();job=self.reserve();self.backend.call(self.payload(),300,job,0)
        self.assertEqual(len(self.original.calls),1)
        with self.assertRaises(ValueError):self.backend.call(self.payload(),300,job,0)
        with self.assertRaises(ValueError):self.reserve()
        self.reserve(turn=1);self.backend.call(self.payload(1000),300,job,1)
        self.assertEqual(len(self.original.calls),2);self.assertEqual(self.quote.call_count,1)

    def test_unknown_reply_retains_reservation_and_cannot_retry_or_advance(self):
        self.admit();job=self.reserve();self.original.fail=True
        with self.assertRaises(TimeoutError):self.backend.call(self.payload(),300,job,0)
        self.assertEqual(len(self.original.reserved),1);self.assertFalse(self.backend.active)
        self.assertFalse(self.backend.returned)
        with self.assertRaises(ValueError):self.backend.call(self.payload(),300,job,0)
        with self.assertRaises(ValueError):self.reserve(turn=1)

    def test_exact_job_and_original_bounds_before_provider(self):
        with self.assertRaises(ValueError):self.reserve()
        self.admit();job=self.reserve();changed=copy.deepcopy(job);changed['seed']+=1
        for payload,task,turn,timeout in [(self.payload(),changed,0,300),(self.payload(6001),job,0,300),(self.payload(),job,False,300),(self.payload(),job,0,361)]:
            with self.assertRaises(ValueError):self.backend.call(payload,timeout,task,turn)
        self.assertFalse(self.original.calls)
        with self.assertRaises(ValueError):self.admit()

    def test_two_inflight_and_atomic_original_reservation(self):
        self.admit();jobs=[self.reserve(i) for i in range(3)]
        def blocked(payload,timeout,job):self.original.enter.wait(3);self.original.release.wait(3);return {'id':'synthetic'}
        self.original.call=blocked
        with ThreadPoolExecutor(max_workers=2) as pool:
            fs=[pool.submit(self.backend.call,self.payload(),300,j,0) for j in jobs[:2]]
            self.original.enter.wait(3)
            try:
                with self.assertRaises(ValueError):self.backend.call(self.payload(),300,jobs[2],0)
            finally:self.original.release.set()
            for f in fs:f.result()
        self.assertEqual(len(self.backend.called),2);self.assertFalse(self.backend.active)

    def test_preflight_failure_and_fixed_stop_never_reserve(self):
        self.quote.side_effect=ValueError('whole plan does not fit')
        with self.assertRaises(ValueError):self.admit()
        self.assertIsNone(self.backend.deadline);self.assertFalse(self.original.reserved)
        self.quote.side_effect=None;self.admit()
        with patch.object(c.bridge.gate,'operating_seconds',side_effect=ValueError('fixed stop')):
            with self.assertRaises(ValueError):self.reserve()
        self.assertFalse(self.original.reserved)

    def test_uncertain_reservation_cannot_be_retried_or_called(self):
        self.admit();job=self.jobs[0]
        self.original.reserve=Mock(side_effect=OSError('synthetic reservation outcome unknown'))
        with self.assertRaises(OSError):self.reserve()
        with self.assertRaises(ValueError):self.reserve()
        with self.assertRaises(ValueError):self.backend.call(self.payload(),300,job,0)
        self.assertEqual(self.original.reserve.call_count,1)
        self.assertFalse(self.backend.reserved);self.assertEqual(len(self.backend.reservation_attempted),1)

if __name__=='__main__':unittest.main()
