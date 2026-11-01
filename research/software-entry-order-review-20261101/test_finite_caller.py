import copy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import finite_caller as c
import guarded_transport as b
import test_matched_protocol as fixture


class Backend:
    scripted=True
    def __init__(self,counter,responses,fault=None):
        self.counter=counter;self.responses=responses;self.fault=fault;self.calls=[];self.reservations=[];self.admissions=[]
        self.lock=threading.Lock();self.barriers={(i,t):threading.Barrier(2) for i in range(4) for t in range(2)}
        self.inflight=0;self.max_inflight=0;self.reserving=0;self.max_reserving=0
    def admit(self,*args):self.admissions.append(args)
    def reserve(self,label,*args):
        with self.lock:self.reserving+=1;self.max_reserving=max(self.max_reserving,self.reserving)
        time.sleep(.002);self.reservations.append(label)
        with self.lock:self.reserving-=1
    def call(self,payload,timeout,job,turn):
        with self.lock:self.calls.append((job['attempt_id'],turn));self.inflight+=1;self.max_inflight=max(self.max_inflight,self.inflight)
        try:
            self.barriers[job['sample'],turn].wait(timeout=20)
            if self.fault=='unknown_second' and job==c.p.jobs('qualification')[0] and turn==1:raise TimeoutError('synthetic unknown second usage')
            response=copy.deepcopy(self.responses[job['attempt_id']][turn])
            if self.fault=='overrun_second' and job==c.p.jobs('qualification')[0] and turn==1:response['usage']['completion_tokens']=8097
            return response
        finally:
            with self.lock:self.inflight-=1
    def check_reply(self,response):pass
    def check_message(self,message):
        if message.get('role')!='assistant':raise ValueError('content-only assistant required')


class FiniteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.MatchedTests.setUpClass();cls.counter=fixture.MatchedTests.counter
        cls.responses={t['job']['attempt_id']:copy.deepcopy(t['responses']) for t in fixture.MatchedTests.traces}
        for responses in cls.responses.values():responses[-1]['choices'][0]['finish_reason']='stop'

    def execute(self,original):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);out=Path(tmp.name)/'phase'
        rows,summary=c.run(b.AtomicDelegation(original),self.counter,out,time.monotonic()+1200)
        return rows,summary,out

    def test_original_sixteen_calls_replay_and_feedback_cost_changes_second_limit(self):
        original=Backend(self.counter,self.responses);rows,summary,out=self.execute(original)
        self.assertTrue(summary['complete']);self.assertEqual(len(original.calls),16)
        self.assertEqual(len(original.reservations),16);self.assertEqual(original.max_inflight,2);self.assertEqual(original.max_reserving,1)
        self.assertEqual(original.admissions[0][:2],([28672]*16,8096))
        report=c.assemble(out,self.counter);self.assertEqual(report['independently_replayed'],8)
        for row in rows:self.assertEqual(row['computed_relation_exposed'],row['job']['arm']=='computed_relation')
        path=next(out.glob('*/request-1.json'));value=json.loads(path.read_text());value['max_tokens']+=1;path.write_text(json.dumps(value))
        with self.assertRaises(ValueError):c.assemble(out,self.counter)

    def test_unknown_second_keeps_first_known_cost_all_reservations_and_peer(self):
        original=Backend(self.counter,self.responses,'unknown_second');rows,summary,out=self.execute(original)
        self.assertFalse(summary['complete']);self.assertEqual(summary['unknown_usage_calls'],1)
        self.assertEqual(len(original.calls),4);self.assertEqual(len(original.reservations),4)
        self.assertIsNone(rows[0]['generation_tokens']);self.assertGreater(rows[0]['known_generation_tokens'],0)
        report=c.assemble(out,self.counter);self.assertEqual(report['independently_replayed'],1)
        self.assertEqual(sum(not r['recorded'] for r in report['rows']),6)

    def test_deadline_after_final_replay_clears_semantic_reward(self):
        original=Backend(self.counter,self.responses)
        original.call=lambda payload,timeout,job,turn:copy.deepcopy(self.responses[job['attempt_id']][turn])
        backend=b.AtomicDelegation(original);deadline=time.monotonic()+1200;backend.admit([28672]*16,8096,deadline)
        clock=time.monotonic;verify=c.p.verify;expired=False
        def current():return clock()+(2000 if expired else 0)
        def replay(*args):
            nonlocal expired
            value=verify(*args);expired=True;return value
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);c.write(out/'assignments.json',c.p.jobs('qualification'));job=c.p.jobs('qualification')[0]
            with patch.object(c.time,'monotonic',side_effect=current),patch.object(c.p,'verify',side_effect=replay):
                row=c.attempt(job,backend,self.counter,out/job['attempt_id'],deadline,threading.Event(),set(),threading.Lock())
            self.assertEqual(row['terminal_reward_observed'],1);self.assertEqual(row['category'],'budget');self.assertIsNone(row['semantic_reward'])
            self.assertFalse(c.assemble(out,self.counter)['complete'])

    def test_known_second_overrun_is_budget_not_unknown(self):
        original=Backend(self.counter,self.responses,'overrun_second');rows,summary,out=self.execute(original)
        self.assertFalse(summary['complete']);self.assertEqual(rows[0]['category'],'budget');self.assertFalse(rows[0]['unknown_usage'])
        self.assertGreater(rows[0]['generation_tokens'],8096);self.assertFalse(c.assemble(out,self.counter)['complete'])

    def test_native_controller_failure_stops_without_semantic_or_unknown_credit(self):
        original=Backend(self.counter,self.responses)
        with patch.object(c.p.RevisionEnvironment,'step',side_effect=OSError('synthetic Native failure')):
            rows,summary,out=self.execute(original)
        self.assertFalse(summary['complete']);self.assertEqual(len(original.calls),2)
        self.assertTrue(all(r['failure_origin']=='native_execution_unverified' and not r['unknown_usage'] for r in rows))
        self.assertFalse(c.assemble(out,self.counter)['complete'])

    def test_unsealed_live_and_duplicate_or_out_of_order_reservations_refused(self):
        with self.assertRaises(ValueError):b.guarded_backend(SimpleNamespace())
        with self.assertRaises(ValueError):b.AtomicDelegation(SimpleNamespace(scripted=False))
        original=Backend(self.counter,self.responses);backend=b.AtomicDelegation(original);deadline=time.monotonic()+1200
        backend.admit([28672]*16,8096,deadline);job=c.p.jobs('qualification')[0];label=job['attempt_id']
        with self.assertRaises(ValueError):backend.reserve(label+':1',28672,1000,deadline)
        def reserve():
            try:backend.reserve(label+':0',28672,6000,deadline);return True
            except ValueError:return False
        with ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(sorted(pool.map(lambda _:reserve(),range(2))),[False,True])
        for d in (float('nan'),time.monotonic()+1201,time.monotonic()-1):
            with tempfile.TemporaryDirectory() as tmp,self.assertRaises(ValueError):c.run(backend,self.counter,Path(tmp)/'phase',d)

    def test_original_linux_supervisor_completion_and_timeout_are_not_remote_cancellation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'phase';backend=b.AtomicDelegation(Backend(self.counter,self.responses))
            result=b.supervise_qualification(backend,self.counter,out,180)
            self.assertEqual(result['status'],'completed');self.assertTrue(result['shutdown_verified'])
            self.assertTrue(c.assemble(out,self.counter)['complete'])
        with tempfile.TemporaryDirectory() as tmp:
            result=b.supervise_qualification(b.AtomicDelegation(Backend(self.counter,self.responses)),self.counter,Path(tmp)/'phase',.01)
            self.assertEqual(result['status'],'timed_out');self.assertTrue(result['shutdown_verified']);self.assertFalse(result['remote_cancellation_attested'])


if __name__=='__main__':unittest.main()
