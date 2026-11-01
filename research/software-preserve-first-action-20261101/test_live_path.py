"""Mocked live plumbing on already-seen qualification inputs; no provider/cases."""
import copy
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import case_materializer as m
import matched_protocol as p
import finite_qualification as finite
import guarded_transport as bridge
import live_screen
import assemble_qualification as assembly
import assess_archive
import test_finite_qualification as fixture


class LivePathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.FiniteTests.setUpClass();cls.counter=fixture.FiniteTests.counter
        cls.replies=copy.deepcopy(fixture.FiniteTests.good)
        for r in cls.replies:r['choices'][0]['finish_reason']='length'

    def test_public_guard_refuses_before_artifact_source_or_native_reads(self):
        with patch.object(m,'sha',side_effect=AssertionError('no artifact read')):
            with self.assertRaises(ValueError):m.materialize(p.jobs('screen')[0],Path('unused'),'a'*64)
            for job in p.jobs('confirmation'):
                with self.assertRaises(ValueError):m.materialize(job,Path('unused'),'a'*64)
        with patch.object(bridge,'verify_clean_source',side_effect=AssertionError('no source read')):
            with self.assertRaises(ValueError):live_screen.require_supervision(SimpleNamespace(case_audit=None,case_audit_sha256=None))

    def test_sealed_audit_binds_method_parent_and_complete_latest_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent_path=Path(tmp)/'parent.json'
            parent=dict(kind='failure-advice-case-audit',task_id='software_repair-ignore-d2',new_seed=3160000,
                        prior_task_seed_pairs=[['software_repair-ignore-d3',2560000]])
            parent_path.write_text(json.dumps(parent))
            prior=sorted(parent['prior_task_seed_pairs']+[['software_repair-ignore-d2',3160000]])
            value=dict(kind='preserve-first-case-audit',method_sha256=m.method_hashes(),parent_audit_path=str(parent_path),
                       parent_audit_sha256=m.sha(parent_path),prior_task_seed_pairs=prior,prior_inventory_sha256=p.native.digest(prior))
            path=Path(tmp)/'audit.json';path.write_text(json.dumps(value));expected=m.sha(path)
            with patch.object(m,'CASE_AUDIT_SHA256',expected),patch.object(m,'verify_inventory',return_value=dict(verified=True,input_overlap=0)) as check:
                self.assertTrue(m.verify_case(p.jobs('screen')[0],path,expected)['verified'])
                self.assertEqual(check.call_count,2)
                self.assertEqual(check.call_args_list[0].args[1],dict(task_id='software_repair-ignore-d2',seed=3160000))
                path.write_text('{}')
                with self.assertRaises(ValueError):m.verify_case(p.jobs('screen')[0],path,expected)

    def test_screen_binding_preserves_original_qualification_native_prompt_and_grade(self):
        # This mocks admission only to exercise the actual binding on an old case.
        # It does not qualify the new screen inventory or provide paid authority.
        with patch.object(m,'verify_case',return_value=dict(verified=True)):
            for arm in p.ARMS:
                old=p.native.qualification_job(arm)
                a=p.native.QualificationTrial(old);b=m.ScreenTrial(old,None,None)
                self.assertEqual(a.messages,b.messages)
                source=json.loads(a.messages[1]['content'])['source'];reply=json.dumps({'content':source})
                self.assertEqual(a.consume(reply,finish_reason='stop'),b.consume(reply,finish_reason='stop'))
                self.assertEqual(b.messages[2]['content'],reply)

    def test_mocked_live_request_archive_and_supervisor_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'screen';original=fixture.Backend(self.replies);original.counter=self.counter
            original.admit=lambda *args:None
            backend=bridge.ConservativeBackend(original)
            factory=lambda job,*args:p.native.QualificationTrial(p.native.qualification_job(job['arm']))
            with patch.object(m,'verify_case',return_value=dict(verified=True)),patch.object(m,'materialize',side_effect=factory):
                _,summary=finite.run_screen(backend,self.counter,out,time.monotonic()+1200,None,'a'*64)
                self.assertTrue(summary['complete']);self.assertFalse(summary['scripted'])
                report=assembly.assemble_screen(out,self.counter,None,'a'*64)
                self.assertEqual(report['independently_replayed'],8);self.assertFalse(report['fitness_eligible'])
                self.assertFalse(assess_archive.assess(out,self.counter,None,'a'*64)['fitness_computed'])
                receipt=out.with_suffix('.supervision.jsonl')
                receipt.write_text(json.dumps(dict(event='terminal',status='timed_out',worker_exitcode=-9,
                    shutdown_verified=True,finished_before_deadline=False))+'\n')
                self.assertFalse(assess_archive.assess(out,self.counter,None,'a'*64)['fitness_computed'])
                receipt.write_text(json.dumps(dict(event='terminal',status='completed',worker_exitcode=0,
                    shutdown_verified=True,finished_before_deadline=True))+'\n')
                scored=assess_archive.assess(out,self.counter,None,'a'*64)
                self.assertEqual(scored['actual_module'],'fitness.mjs:scoreCell')
                self.assertFalse(scored['selection_passed'])
                trace_path=next(out.glob('*.trace.json'));trace=json.loads(trace_path.read_text())
                trace['execution_sha256']['matched_protocol.py']='f'*64;trace_path.write_text(json.dumps(trace))
                with self.assertRaises(ValueError):assembly.assemble_screen(out,self.counter,None,'a'*64)

    def test_mocked_live_unknown_usage_archive_remains_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'screen';original=fixture.Backend([TimeoutError('synthetic unknown')]);original.counter=self.counter
            original.admit=lambda *args:None
            backend=bridge.ConservativeBackend(original)
            factory=lambda job,*args:p.native.QualificationTrial(p.native.qualification_job(job['arm']))
            with patch.object(m,'verify_case',return_value=dict(verified=True)),patch.object(m,'materialize',side_effect=factory):
                _,summary=finite.run_screen(backend,self.counter,out,time.monotonic()+1200,None,'a'*64)
                report=assembly.assemble_screen(out,self.counter,None,'a'*64)
            self.assertFalse(report['complete']);self.assertEqual(summary['unknown_usage_calls'],1)
            self.assertEqual(len(original.reservations),1)
            self.assertEqual(sum(not r['recorded'] for r in report['rows']),7)

    def test_terminal_observation_counts_against_actual_provider_context(self):
        response=copy.deepcopy(fixture.FiniteTests.good[0])
        response['usage']['prompt_tokens']=24576-response['usage']['completion_tokens']
        # The generation fits exactly; the real terminal observation does not.
        with self.assertRaises(ValueError):p.observe_scripted(p.jobs('qualification')[0],response,self.counter)


if __name__=='__main__':unittest.main()
