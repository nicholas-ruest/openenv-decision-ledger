"""Finite orchestrator qualification; no provider transport or new cases."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import finite_caller as c
from replay_matched import verify


class Backend:
    scripted=True
    def __init__(self,counter,fail_at=None,deny_at=None,unknown_at=None):
        self.counter=counter;self.fail_at=fail_at;self.deny_at=deny_at;self.unknown_at=unknown_at
        self.calls=[];self.reservations=[];self.reserve_attempts=0
    def reserve(self,label,prompt,completion,deadline):
        self.reserve_attempts+=1
        if self.reserve_attempts==self.deny_at:raise ValueError('reservation refused')
        self.reservations.append(label)
    def check_reply(self,r):pass
    def check_message(self,m):pass
    def call(self,payload,timeout,job):
        self.calls.append(payload)
        if len(self.calls)==self.fail_at:raise TimeoutError('unknown usage')
        from repair_env.tasks import make_task
        source=make_task(job['task_id'],job['seed']).reference_source.replace('return table[len(tokens)][len(word)]','return False')
        text=json.dumps(dict(content=source if len(payload['messages'])==2 else ''))
        usage=dict(prompt_tokens=self.counter.context(payload['messages']),completion_tokens=self.counter.count(text))
        if len(self.calls)==self.unknown_at:usage['completion_tokens']=None
        return dict(id=job['attempt_id']+':reply:'+str(len(self.calls)),usage=usage,
            choices=[dict(finish_reason='stop',message=dict(role='assistant',content=text))])


class CallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('finite_helper_counter',c.protocol.ROOT/'integrations/openenv-arena/scripts/calibrate.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        cls.counter=m.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=Path(os.environ['HELPER_TEST_TOKENIZER']),tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))

    def test_all_four_chunks_independently_replay_and_stay_scripted(self):
        with tempfile.TemporaryDirectory() as tmp:
            ids=[];calls=0
            for i in range(4):
                b=Backend(self.counter);out=Path(tmp)/str(i)
                rows,done=c.qualification_chunk(i,b,self.counter,out,time.monotonic()+60)
                self.assertFalse(done['stopped_on_failure']);self.assertEqual(done['recorded_attempts'],2)
                self.assertEqual(len(b.reservations),len(b.calls));self.assertEqual(len(b.calls),4)
                for trace in out.glob('*.trace.json'):
                    proof=verify(json.loads(trace.read_text()),self.counter)
                    self.assertFalse(proof['live_evidence'])
                ids += [r['job']['attempt_id'] for r in rows];calls+=done['observed_calls']
            self.assertEqual(len(set(ids)),8);self.assertEqual(calls,16)

    def test_unknown_usage_after_known_reply_retains_reservations_and_stops(self):
        for kwargs in [dict(fail_at=2),dict(unknown_at=2)]:
            with self.subTest(kwargs=kwargs),tempfile.TemporaryDirectory() as tmp:
                b=Backend(self.counter,**kwargs);out=Path(tmp)/'new'
                rows,done=c.qualification_chunk(0,b,self.counter,out,time.monotonic()+60)
                self.assertEqual(len(b.reservations),2);self.assertEqual(len(b.calls),2)
                self.assertIsNone(rows[0]['generation_tokens']);self.assertTrue(rows[0]['unknown_usage'])
                self.assertEqual(done['uncalled_assignments'],1);self.assertTrue(done['stopped_on_failure'])
                self.assertEqual(list(out.glob('*.trace.json')),[])

    def test_denied_reservation_never_calls_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=Backend(self.counter,deny_at=2)
            rows,done=c.qualification_chunk(0,b,self.counter,Path(tmp)/'new',time.monotonic()+60)
            self.assertEqual(len(b.calls),1);self.assertEqual(len(b.reservations),1)
            self.assertEqual(rows[0]['category'],'budget');self.assertFalse(rows[0]['unknown_usage'])
            self.assertIsInstance(rows[0]['generation_tokens'],int)

    def test_native_initialization_failure_and_reused_archive_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=Backend(self.counter);out=Path(tmp)/'new'
            with patch.object(c.protocol,'QualificationTrial',side_effect=RuntimeError('Native unavailable')):
                rows,done=c.qualification_chunk(0,b,self.counter,out,time.monotonic()+60)
            self.assertEqual(rows[0]['category'],'execution');self.assertEqual(b.calls,[])
            with self.assertRaises(ValueError):c.qualification_chunk(0,b,self.counter,out,time.monotonic()+60)

    def test_live_execution_has_two_source_bound_blocks_before_materialization(self):
        with patch.dict(os.environ,LIVE_CASE_AUDIT_SHA256='a'*64),patch.object(c.protocol,'materialize',side_effect=AssertionError('must not reach Native')):
            with self.assertRaises(ValueError):c.require_live_ready()
        with patch.object(c,'LIVE_CASE_AUDIT_SHA256','a'*64):
            with self.assertRaises(ValueError):c.require_live_ready()
        result=subprocess.run([sys.executable,'-B',str(Path(c.__file__)),'--execute'],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('unsealed live source/case admission',result.stderr)

    def test_deadline_expiry_after_reservation_or_native_step_is_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            now=[0.0];b=Backend(self.counter);reserve=b.reserve
            def delayed_reserve(*args):
                reserve(*args);now[0]=700.0
            b.reserve=delayed_reserve
            with patch.object(c.time,'monotonic',side_effect=lambda:now[0]):
                rows,done=c.qualification_chunk(0,b,self.counter,Path(tmp)/'reserve',1200)
            self.assertEqual(len(b.reservations),1);self.assertEqual(b.calls,[])
            self.assertEqual(rows[0]['category'],'budget')
            now=[0.0];b=Backend(self.counter);consume=c.protocol.QualificationTrial.consume
            def delayed_native(trial,text):
                result=consume(trial,text);now[0]=700.0;return result
            with patch.object(c.time,'monotonic',side_effect=lambda:now[0]),patch.object(c.protocol.QualificationTrial,'consume',new=delayed_native):
                rows,done=c.qualification_chunk(0,b,self.counter,Path(tmp)/'native',1200)
            self.assertEqual(rows[0]['category'],'budget')
            self.assertTrue(done['stopped_on_failure'])


if __name__=='__main__':unittest.main()
