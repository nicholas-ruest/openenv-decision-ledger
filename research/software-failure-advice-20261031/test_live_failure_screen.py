"""Mocked live-path fault injection, Native case3100000 only. No provider.

Source guards are mocked only inside temporary controls. No future procedural
case, private audit artifact or persistent live-performance result is created.
"""
import copy,json,subprocess,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import failure_protocol as p
import finite_qualification as c
import failure_materializer as m
import live_advice_screen as worker
from assemble_archives import assemble,assemble_screen
import test_finite_qualification as fixture


def old(job):return next(j for j in p.jobs('qualification') if j['arm']==job['arm'] and j['sample']==job['sample'])


class MockBackend(fixture.Backend):
    scripted=False
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.quotes=[]
    def admit(self,*args):self.quotes.append(args)
    def call(self,payload,timeout,job):
        result=super().call(payload,timeout,job)
        if len(payload['messages'])>2 and job['arm']=='standard_revision':
            text=json.dumps(dict(content=json.loads(payload['messages'][1]['content'])['source']))
            result['choices'][0]['message']['content']=text;result['usage']['completion_tokens']=self.counter.count(text)
        return result


def score(report):
    module=Path(__file__).with_name('assess_archives.mjs').as_uri()
    js="import {readFileSync} from 'node:fs';import {assessScreenArchive} from "+json.dumps(module)+";console.log(JSON.stringify(assessScreenArchive(JSON.parse(readFileSync(0,'utf8')))));"
    out=subprocess.run(['node','--input-type=module','-e',js],input=json.dumps(report),text=True,capture_output=True,check=True)
    return json.loads(out.stdout)


class LivePathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixture.FiniteTests.setUpClass();cls.counter=fixture.FiniteTests.counter
    def mock_guards(self):
        return patch.object(c,'require_live_ready',return_value=dict(case_audit_sha256='a'*64)),patch.object(p,'materialize',side_effect=lambda job,*args:p.QualificationTrial(old(job)))
    def test_default_guard_precedes_finance_private_reads_and_worker_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=MockBackend(self.counter)
            with self.assertRaises(ValueError):c.run_screen_chunk(0,b,self.counter,Path(tmp)/'new',time.monotonic()+60,'unused','a'*64)
            self.assertEqual((b.calls,b.reserved,b.quotes),([],[],[]))
            with patch.object(worker.b,'verify_clean_source',side_effect=AssertionError('no source inspection')):
                args=['live_advice_screen.py','--execute','--chunk','0','--receipt','r','--reconciliation','a','--tokenizer','t','--output','o','--case-audit','c','--case-audit-sha256','a'*64,'--expected-source','s','--amendment-sha256','b'*64]
                with patch('sys.argv',args),self.assertRaises(ValueError):worker.main()
    def test_all_eight_requests_replay_and_selection_requires_actual_advice_exposure(self):
        one,two=self.mock_guards()
        with one,two,tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);paths=[]
            for i in range(4):
                out=root/str(i);paths.append(out);b=MockBackend(self.counter)
                rows,done=c.run_screen_chunk(i,b,self.counter,out,time.monotonic()+120,'unused','a'*64)
                self.assertEqual(b.quotes[0][:2],([28672]*16,8096));self.assertFalse(done['scripted'])
                receipt=dict(event='terminal',status='completed',worker_exitcode=0,shutdown_verified=True,finished_before_deadline=True)
                out.with_suffix('.supervision.jsonl').write_text(json.dumps(receipt)+'\n')
            report=assemble_screen(paths,self.counter,'unused','a'*64);result=score(report)
            self.assertTrue(report['complete']);self.assertEqual(report['actual_calls'],16)
            self.assertEqual(report['independently_replayed'],8);self.assertTrue(result['selection_passed']);self.assertFalse(result['model_improvement'])
            self.assertEqual(result['groups'][1]['advice_deliveries'],4)
            no_exposure=copy.deepcopy(report)
            for r in no_exposure['rows']:
                if r['job']['arm']=='focused_failure_advice':
                    r['completion_with_observations']-=r['advice_observation_tokens'];r['advice_observation_tokens']=0;r['advice_deliveries']=0
            self.assertFalse(score(no_exposure)['selection_passed'])
            with self.assertRaises(ValueError):assemble(paths,self.counter)
            args=SimpleNamespace(chunk=3,prior=paths[:3],output=root/'new',case_audit='unused',case_audit_sha256='a'*64)
            worker.prior_chunks(args,self.counter)
            paths[0].with_suffix('.supervision.jsonl').write_text(json.dumps(dict(receipt,status='worker_failed'))+'\n')
            with self.assertRaises(ValueError):worker.prior_chunks(args,self.counter)
            # Alter both raw and trace request hashes: independent reconstruction
            # must still reject, rather than merely checking they agree.
            events=[json.loads(l) for l in (paths[0]/'events.jsonl').read_text().splitlines()]
            calling=next(e for e in events if e['event']=='calling');calling['request_sha256']='b'*64
            (paths[0]/'events.jsonl').write_text('\n'.join(json.dumps(e) for e in events))
            f=paths[0]/(p.jobs('screen')[0]['attempt_id']+'.trace.json');trace=json.loads(f.read_text());trace['requests'][0]['request_sha256']='b'*64;f.write_text(json.dumps(trace))
            with self.assertRaises(ValueError):assemble_screen(paths,self.counter,'unused','a'*64)
    def test_unknown_usage_after_known_reply_keeps_reservations_and_suppresses_fitness(self):
        one,two=self.mock_guards()
        with one,two,tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);b=MockBackend(self.counter,unknown=2);out=root/'0'
            rows,done=c.run_screen_chunk(0,b,self.counter,out,time.monotonic()+60,'unused','a'*64)
            self.assertEqual(len(b.reserved),2);self.assertEqual(len(b.calls),2);self.assertIsNone(rows[0]['generation_tokens'])
            report=assemble_screen([out]+[root/str(i) for i in range(1,4)],self.counter,'unused','a'*64)
            self.assertEqual(report['unexecuted'],7);self.assertIsNone(score(report)['actual_module']);self.assertFalse(score(report)['selection_passed'])
    def test_live_trace_source_and_scripted_relabelling_are_refused_before_native(self):
        with patch.object(p,'materialize',side_effect=AssertionError('no Native')):
            for trace in [dict(job=p.jobs('screen')[0],scripted=True,live_evidence=False),dict(job=p.jobs('screen')[0],scripted=False,live_evidence=True,case_audit_sha256='a'*64,execution_sha256={})]:
                with self.assertRaises(ValueError):p.verify_screen(trace,self.counter,'unused','a'*64)
    def test_actual_proc_worker_argv_blocks_a_duplicate_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);entry=root/'424242';entry.mkdir();(entry/'cmdline').write_bytes(b'/usr/bin/python\x00/home/ruv/caller.py\x00--execute\x00')
            original=Path.iterdir
            with patch.object(Path,'iterdir',lambda path:original(root) if str(path)=='/proc' else original(path)):
                with self.assertRaises(ValueError):worker.no_other_workers()


if __name__=='__main__':unittest.main()
