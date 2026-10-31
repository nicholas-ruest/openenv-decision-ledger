"""Synthetic live-path fault injection on already-used3100000 only.

Mocks remove the source seal solely inside temporary controls. No provider,
private case artifact, future Native case or persistent live result is created.
"""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import finite_caller as c
import matched_protocol as p
import live_screen as worker
from assemble_phase import assemble,assemble_screen
from replay_matched import verify_screen
import test_finite_caller as fixture


def existing(job):
    return next(j for j in p.jobs('qualification') if j['sample']==job['sample'] and j['arm']==job['arm'])


class MockLive(fixture.Backend):
    scripted=False
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.quotes=[]
    def admit(self,*args):self.quotes.append(args)
    def call(self,payload,timeout,job):return super().call(payload,timeout,existing(job))


def score(a):
    module=Path(__file__).with_name('assess_qualification.mjs').as_uri()
    js="import {readFileSync} from 'node:fs';import {assessScreen} from "+json.dumps(module)+";console.log(JSON.stringify(assessScreen(JSON.parse(readFileSync(0,'utf8')))));"
    value=subprocess.run(['node','--input-type=module','-e',js],input=json.dumps(a),text=True,capture_output=True,check=True)
    return json.loads(value.stdout)


class ScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixture.CallerTests.setUpClass();cls.counter=fixture.CallerTests.counter
    def controls(self):
        return patch.object(c,'require_live_ready',return_value=dict(case_audit_sha256='a'*64)),patch.object(p,'materialize',side_effect=lambda j,*a:p.QualificationTrial(existing(j)))

    def test_unsealed_entry_cannot_quote_reserve_or_construct_a_trial(self):
        b=MockLive(self.counter)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):c.screen_chunk(0,b,self.counter,Path(tmp)/'new',time.monotonic()+60,Path('missing'),'a'*64)
        self.assertEqual((b.quotes,b.reservations,b.calls),([],[],[]))
        with patch.object(worker.bridge,'verify_clean_source',side_effect=AssertionError('must not inspect source')):
            with patch('sys.argv',['live_screen.py','--execute','--chunk','0','--receipt','r','--reconciliation','f','--tokenizer','t','--output','o','--case-audit','c','--expected-source','s','--case-audit-sha256','a'*64,'--amendment-sha256','b'*64]):
                with self.assertRaises(ValueError):worker.main()

    def test_complete_original_schedule_replays_and_quotes_all_sixteen_calls(self):
        one,two=self.controls()
        with one,two,tempfile.TemporaryDirectory() as tmp:
            paths=[]
            for i in range(4):
                out=Path(tmp)/str(i);paths.append(out);b=MockLive(self.counter)
                rows,done=c.screen_chunk(i,b,self.counter,out,time.monotonic()+120,'unused','a'*64)
                self.assertEqual(b.quotes[0][:2],([28672]*16,8096));self.assertFalse(done['scripted'])
            report=assemble_screen(paths,self.counter,'unused','a'*64);assessment=score(report)
            self.assertTrue(report['complete']);self.assertEqual(report['actual_calls'],16)
            self.assertEqual(report['independently_replayed'],8)
            self.assertTrue(assessment['selection_passed']);self.assertFalse(assessment['model_improvement'])
            self.assertEqual(assessment['groups'][1]['controller_assisted_full'],4)
            self.assertEqual(assessment['groups'][1]['model_response_only_full'],0)
            with self.assertRaises(ValueError):assemble(paths,self.counter)
            bad=copy.deepcopy(report);bad['rows'][0]['job']['attempt_id']='b'*64
            with self.assertRaises(subprocess.CalledProcessError):score(bad)
            args=SimpleNamespace(chunk=3,prior=paths[:3],output=Path(tmp)/'new',counter=self.counter,case_audit='unused',case_audit_sha256='a'*64)
            worker.prior_chunks(args)
            args.prior=[paths[0],paths[0],paths[2]]
            with self.assertRaises(ValueError):worker.prior_chunks(args)

    def test_unknown_usage_stops_later_chunks_and_suppresses_fitness(self):
        one,two=self.controls()
        with one,two,tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'0';b=MockLive(self.counter,fail_at=2)
            rows,done=c.screen_chunk(0,b,self.counter,out,time.monotonic()+60,'unused','a'*64)
            paths=[out]+[root/str(i) for i in range(1,4)]
            report=assemble_screen(paths,self.counter,'unused','a'*64);assessment=score(report)
            self.assertEqual(len(b.reservations),2);self.assertIsNone(rows[0]['generation_tokens'])
            self.assertEqual(report['unexecuted'],7);self.assertFalse(assessment['selection_passed']);self.assertIsNone(assessment['actual_module'])
            args=SimpleNamespace(chunk=1,prior=[out],output=root/'new',counter=self.counter,case_audit='unused',case_audit_sha256='a'*64)
            with self.assertRaises(ValueError):worker.prior_chunks(args)

    def test_wrong_case_and_scripted_trace_cannot_be_live_replay(self):
        with patch.object(p,'materialize',side_effect=AssertionError('must not construct')):
            with self.assertRaises(ValueError):verify_screen(dict(scripted=True,job=p.jobs('screen')[0]),self.counter,'unused','a'*64)
            with self.assertRaises(ValueError):verify_screen(dict(scripted=False,job=p.jobs('screen')[0],case_audit_sha256='b'*64),self.counter,'unused','a'*64)

    def test_worker_checks_actual_proc_argv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);entry=root/'424242';entry.mkdir();(entry/'cmdline').write_bytes(b'/usr/bin/python\x00/home/ruv/caller.py\x00--execute\x00')
            original=Path.iterdir
            with patch.object(Path,'iterdir',lambda path:original(root) if str(path)=='/proc' else original(path)):
                with self.assertRaises(ValueError):worker.no_other_workers()


if __name__=='__main__':unittest.main()
