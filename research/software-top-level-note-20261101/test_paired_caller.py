from concurrent.futures import ThreadPoolExecutor
import copy
from datetime import datetime
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo
import paired_caller as c
import paired_transport as b
import test_matched_note as fixtures


class OriginalBackend:
    scripted=True
    def __init__(self,counter,responses,*,barrier=True,fault=None):
        self.counter=counter;self.responses=responses;self.barrier=barrier;self.fault=fault
        self.barriers=[threading.Barrier(2) for _ in range(4)]
        self.meta=threading.Lock();self.calls=[];self.reservations=[];self.admissions=[]
        self.inflight=0;self.max_inflight=0;self.reserving=0;self.max_reserving=0
    def admit(self,*args):self.admissions.append(args)
    def reserve(self,label,*args):
        with self.meta:self.reserving+=1;self.max_reserving=max(self.max_reserving,self.reserving)
        time.sleep(.002)
        try:
            if self.fault=='denial' and label==c.p.jobs('qualification')[0]['attempt_id']+':0':raise ValueError('synthetic denial')
            self.reservations.append(label)
        finally:
            with self.meta:self.reserving-=1
    def call(self,payload,timeout,job):
        with self.meta:
            self.calls.append(job['attempt_id']);self.inflight+=1;self.max_inflight=max(self.max_inflight,self.inflight)
        try:
            if self.barrier:self.barriers[job['sample']].wait(timeout=15)
            if self.fault=='unknown' and job==c.p.jobs('qualification')[0]:raise TimeoutError('synthetic unknown usage')
            return copy.deepcopy(self.responses[job['attempt_id']])
        finally:
            with self.meta:self.inflight-=1
    def check_reply(self,response):pass
    def check_message(self,message):
        if message.get('role')!='assistant':raise ValueError('invalid provider role')


class PairedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.MatchedTests.setUpClass();cls.counter=fixtures.MatchedTests.counter
        cls.responses={t['job']['attempt_id']:t['response'] for t in fixtures.MatchedTests.traces}
        # The original fixture's final provider error is replaced by a known
        # format failure, so all eight model outcomes can complete in this control.
        last=c.p.jobs('qualification')[-1]['attempt_id']
        cls.responses[last]=copy.deepcopy(cls.responses[last]);cls.responses[last]['choices'][0]['finish_reason']='stop'

    def execute(self,original):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);out=Path(tmp.name)/'phase'
        rows,summary=c.run(b.AtomicDelegation(original),self.counter,out,time.monotonic()+1200)
        return rows,summary,out

    def test_all_eight_parallel_pair_outcomes_replay_and_keep_program_errors(self):
        original=OriginalBackend(self.counter,self.responses)
        rows,summary,out=self.execute(original)
        self.assertTrue(summary['complete']);self.assertFalse(summary['selection_passed'])
        self.assertEqual(len(original.calls),8);self.assertEqual(len(set(original.calls)),8)
        self.assertEqual(original.max_inflight,2);self.assertEqual(original.max_reserving,1)
        self.assertEqual(original.admissions[0][:2],([28672]*16,8096))
        self.assertEqual(rows[1]['failure_origin'],'model_program_rejection');self.assertEqual(rows[1]['terminal_reward_observed'],0)
        self.assertEqual(rows[2]['failure_origin'],'model_program_runtime_error')
        report=c.assemble(out,self.counter);self.assertEqual(report['independently_replayed'],8)
        record=out/c.p.jobs('qualification')[0]['attempt_id']/'record.json';bad=json.loads(record.read_text());bad['category']='wrong';record.write_text(json.dumps(bad))
        with self.assertRaises(ValueError):c.assemble(out,self.counter)

    def test_unknown_in_one_request_keeps_both_original_reservations_and_stops_new_pairs(self):
        original=OriginalBackend(self.counter,self.responses,fault='unknown')
        rows,summary,out=self.execute(original)
        self.assertFalse(summary['complete']);self.assertEqual(summary['unknown_usage_calls'],1)
        self.assertEqual(len(original.calls),2);self.assertEqual(len(original.reservations),2)
        self.assertIsNone(rows[0]['generation_tokens']);self.assertTrue(rows[0]['unknown_usage'])
        report=c.assemble(out,self.counter);self.assertFalse(report['fitness_eligible'])
        self.assertEqual(sum(not r['recorded'] for r in report['rows']),6)

    def test_denied_reservation_cannot_start_an_unreserved_call_or_later_pair(self):
        original=OriginalBackend(self.counter,self.responses,barrier=False,fault='denial')
        rows,summary,_=self.execute(original)
        self.assertFalse(summary['complete']);self.assertLessEqual(len(original.calls),1)
        self.assertEqual(rows[0]['category'],'budget')
        self.assertNotIn(c.p.jobs('qualification')[0]['attempt_id'],original.calls)

    def test_native_step_exception_stops_new_pairs_without_becoming_model_failure(self):
        from repair_env.direct_environment import DirectRepairEnvironment
        original=OriginalBackend(self.counter,self.responses)
        with patch.object(DirectRepairEnvironment,'step',side_effect=RuntimeError('synthetic Native infrastructure failure')):
            rows,summary,out=self.execute(original)
            report=c.assemble(out,self.counter)
        self.assertFalse(summary['complete']);self.assertEqual(len(original.calls),2)
        self.assertTrue(all(r['failure_origin']=='native_execution_unverified' for r in rows))
        self.assertTrue(all(not r['unknown_usage'] for r in rows));self.assertFalse(report['fitness_eligible'])

    def test_actual_token_overrun_is_known_budget_failure_and_stops_new_pairs(self):
        replies=copy.deepcopy(self.responses);first=c.p.jobs('qualification')[0]['attempt_id']
        replies[first]['usage']['completion_tokens']=6001
        original=OriginalBackend(self.counter,replies)
        rows,summary,out=self.execute(original)
        self.assertFalse(summary['complete']);self.assertEqual(len(original.calls),2)
        self.assertEqual(rows[0]['category'],'budget');self.assertFalse(rows[0]['unknown_usage'])
        self.assertEqual(rows[0]['generation_tokens'],6001)
        self.assertFalse(c.assemble(out,self.counter)['fitness_eligible'])

    def test_duplicate_reserve_and_call_are_atomic_and_failed_calls_consumed(self):
        original=OriginalBackend(self.counter,self.responses,barrier=False,fault='unknown')
        backend=b.AtomicDelegation(original);deadline=time.monotonic()+1200
        backend.admit([28672]*8,6000,deadline);job=c.p.jobs('qualification')[0];label=job['attempt_id']+':0'
        def reserve():
            try:backend.reserve(label,28672,6000,deadline);return True
            except ValueError:return False
        with ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(sorted(pool.map(lambda _:reserve(),range(2))),[False,True])
        payload=dict(c.p.n.original.SAMPLING,messages=[],max_tokens=6000)
        def call():
            try:backend.call(payload,1,job);return 'returned'
            except TimeoutError:return 'unknown'
            except ValueError:return 'denied'
        with ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(sorted(pool.map(lambda _:call(),range(2))),['denied','unknown'])
        self.assertEqual(len(original.reservations),1);self.assertEqual(len(original.calls),1)
        self.assertIn(label,backend.called)

    def test_unsealed_live_guard_and_original_limits_cannot_be_bypassed(self):
        with patch.object(c.p.n,'QualificationTrial',side_effect=AssertionError('no capture')):
            value=c.plan()
        self.assertTrue(value['live_continuation_policy_frozen']);self.assertEqual(value['max_inflight_requests'],2)
        self.assertFalse(value['live_execution_ready']);self.assertEqual(len(value['screen_jobs']),8)
        with patch.object(b.n.original,'load',side_effect=AssertionError('no backend import')):
            with self.assertRaises(ValueError):b.guarded_backend(SimpleNamespace())
        with self.assertRaises(ValueError):c.run(SimpleNamespace(scripted=False),self.counter,Path('unused'),time.monotonic()+1200)
        for deadline in (float('nan'),time.monotonic()+1201,time.monotonic()-1):
            with tempfile.TemporaryDirectory() as tmp,self.assertRaises(ValueError):
                c.run(b.AtomicDelegation(OriginalBackend(self.counter,self.responses)),self.counter,Path(tmp)/'phase',deadline)
        for row in [dict(category='provider',failure_origin='provider_failure'),
                    dict(category='execution',failure_origin='native_execution_unverified'),
                    dict(category='execution',failure_origin='model_program_rejection',native_compile_rejected=True,terminal_reward_observed=1,semantic_reward=None)]:
            self.assertTrue(c.stops_phase(row))

    def test_actual_whole_phase_supervisor_completion_and_thread_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'complete';backend=b.AtomicDelegation(OriginalBackend(self.counter,self.responses))
            result=b.supervise_qualification(backend,self.counter,out,120,now=datetime(2026,11,1,12,tzinfo=ZoneInfo('America/Toronto')))
            self.assertEqual(result['status'],'completed');self.assertTrue(result['shutdown_verified'])
            self.assertTrue(result['finished_before_deadline']);self.assertTrue(c.assemble(out,self.counter)['complete'])
            with self.assertRaises(ValueError):b.supervise_qualification(backend,self.counter,out,120)
        with tempfile.TemporaryDirectory() as tmp:
            result=b.supervise_qualification(b.AtomicDelegation(OriginalBackend(self.counter,self.responses)),self.counter,Path(tmp)/'timeout',.01)
            self.assertEqual(result['status'],'timed_out');self.assertTrue(result['shutdown_verified'])
            self.assertFalse(result['remote_cancellation_attested'])


if __name__=='__main__':unittest.main()
