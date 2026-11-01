"""Mock live plumbing on previously seen qualification cases; no new cases/API."""
import copy
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import sealed_case as m
import paired_caller as c
import paired_transport as b
import live_pairs
import assess_pairs
import test_paired_caller as fixture


class LivePairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.PairedTests.setUpClass();cls.counter=fixture.PairedTests.counter
        cls.responses={new['attempt_id']:copy.deepcopy(fixture.PairedTests.responses[old['attempt_id']])
            for new,old in zip(c.p.jobs('screen'),c.p.jobs('qualification'))}

    def backend(self,responses=None):
        original=fixture.OriginalBackend(self.counter,responses or self.responses)
        original.scripted=False
        return original,b.AtomicDelegation(original)

    def old_trial(self,job,*args):
        return c.p.n.QualificationTrial(c.p.n.job(job['arm']))

    def test_unsealed_public_live_gate_refuses_before_private_source_or_backend_reads(self):
        with patch.object(m,'sha',side_effect=AssertionError('no private read')):
            for phase in ('screen','confirmation'):
                with self.assertRaises(ValueError):m.materialize(c.p.jobs(phase)[0],Path('unused'),'a'*64)
        with patch.object(b.existing,'verify_clean_source',side_effect=AssertionError('no source access')):
            with self.assertRaises(ValueError):live_pairs.require_supervision(SimpleNamespace(case_audit=None,case_audit_sha256=None))
        with tempfile.TemporaryDirectory() as tmp,patch.object(c,'trial_for',side_effect=AssertionError('no case capture')):
            _,backend=self.backend()
            with self.assertRaises(ValueError):c.run_screen(backend,self.counter,Path(tmp)/'screen',time.monotonic()+1200,None,'a'*64)
        with patch.object(m,'CASE_AUDIT_SHA256','a'*64),patch.object(m,'sha',side_effect=AssertionError('no confirmation read')):
            with self.assertRaises(ValueError):m.verify_case(c.p.jobs('confirmation')[0],None,'a'*64)

    def test_immutable_lease_requires_both_closed_anchors_and_complete_latest_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);older_path=root/'older.json';parent_path=root/'parent.json';path=root/'new.json'
            older=dict(kind='failure-advice-case-audit',task_id='software_repair-ignore-d2',new_seed=3160000,
                prior_task_seed_pairs=[['software_repair-ignore-d3',2560000]])
            older_path.write_text(json.dumps(older))
            parent_prior=sorted(older['prior_task_seed_pairs']+[['software_repair-ignore-d2',3160000]])
            parent=dict(kind='preserve-first-case-audit',task_id='software_repair-ignore-d3',new_seed=3180000,
                method_sha256=m._prior().method_hashes(),parent_audit_path=str(older_path),parent_audit_sha256=m.sha(older_path),
                prior_task_seed_pairs=parent_prior,prior_inventory_sha256=c.p.n.original.digest(parent_prior))
            parent_path.write_text(json.dumps(parent))
            prior=sorted(parent_prior+[['software_repair-ignore-d3',3180000]])
            value=dict(kind='top-level-note-case-audit',method_sha256=m.method_hashes(),parent_audit_path=str(parent_path),
                parent_audit_sha256=m.sha(parent_path),prior_task_seed_pairs=prior,prior_inventory_sha256=c.p.n.original.digest(prior))
            path.write_text(json.dumps(value));expected=m.sha(path)
            with patch.object(m,'CASE_AUDIT_SHA256',expected),patch.object(m.prior,'verify_inventory',return_value=dict(verified=True,input_overlap=0)) as verify:
                self.assertTrue(m.verify_case(c.p.jobs('screen')[0],path,expected)['verified'])
                self.assertEqual(verify.call_count,3)
                self.assertEqual(verify.call_args_list[1].args[1],dict(task_id='software_repair-ignore-d3',seed=3180000))
                path.write_text('{}')
                with self.assertRaises(ValueError):m.verify_case(c.p.jobs('screen')[0],path,expected)
            value['prior_task_seed_pairs']=parent_prior;value['prior_inventory_sha256']=c.p.n.original.digest(parent_prior)
            path.write_text(json.dumps(value));expected=m.sha(path)
            with patch.object(m,'CASE_AUDIT_SHA256',expected),patch.object(m.prior,'verify_inventory',return_value=dict(verified=True)):
                with self.assertRaises(ValueError):m.verify_case(c.p.jobs('screen')[0],path,expected)

    def test_actual_screen_binding_matches_original_syntax_note_on_old_input(self):
        with patch.object(m,'verify_case',return_value=dict(verified=True)):
            for arm in c.p.n.ARMS:
                old=c.p.n.job(arm);a=c.p.n.QualificationTrial(old);new=m.ScreenTrial(old,None,None)
                self.assertEqual(a.messages,new.messages)
                source=json.loads(a.messages[1]['content'])['source'];reply=json.dumps(dict(content=source))
                self.assertEqual(a.consume(reply,finish_reason='stop'),new.consume(reply,finish_reason='stop'))
                self.assertEqual(new.messages[2]['content'],reply)

    def test_mock_live_pair_archives_require_original_successful_supervisor_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'screen';original,backend=self.backend()
            with patch.object(m,'verify_case',return_value=dict(verified=True)),patch.object(m,'materialize',side_effect=self.old_trial):
                _,summary=c.run_screen(backend,self.counter,out,time.monotonic()+1200,None,'a'*64)
                self.assertTrue(summary['complete']);self.assertFalse(summary['scripted'])
                report=c.assemble(out,self.counter,'screen',None,'a'*64)
                self.assertEqual(report['independently_replayed'],8);self.assertEqual(original.max_inflight,2)
                self.assertFalse(assess_pairs.assess(out,self.counter,None,'a'*64)['fitness_computed'])
                receipt=out.with_suffix('.supervision.jsonl')
                receipt.write_text(json.dumps(dict(event='terminal',status='timed_out',worker_exitcode=-9,shutdown_verified=True,finished_before_deadline=False))+'\n')
                self.assertFalse(assess_pairs.assess(out,self.counter,None,'a'*64)['fitness_computed'])
                receipt.write_text(json.dumps(dict(event='terminal',status='completed',worker_exitcode=0,shutdown_verified=True,finished_before_deadline=True))+'\n')
                result=assess_pairs.assess(out,self.counter,None,'a'*64)
                self.assertEqual(result['actual_module'],'fitness.mjs:scoreCell');self.assertFalse(result['selection_passed'])
                self.assertEqual(sum(g['model_program_failures'] for g in result['groups']),2)
                summary['complete']=False;(out/'complete.json').write_text(json.dumps(summary))
                self.assertFalse(assess_pairs.assess(out,self.counter,None,'a'*64)['fitness_computed'])
                trace_path=next(out.glob('*/trace.json'));trace=json.loads(trace_path.read_text())
                trace['execution_sha256']['paired_caller.py']='f'*64;trace_path.write_text(json.dumps(trace))
                with self.assertRaises(ValueError):c.assemble(out,self.counter,'screen',None,'a'*64)

    def test_live_unknown_usage_preserves_reserved_peer_and_uncalled_denominator(self):
        original,backend=self.backend();original_call=original.call
        def call(payload,timeout,job):
            if job==c.p.jobs('screen')[0]:
                with original.meta:
                    original.calls.append(job['attempt_id']);original.inflight+=1;original.max_inflight=max(original.max_inflight,original.inflight)
                try:original.barriers[0].wait(timeout=15);raise TimeoutError('synthetic unknown')
                finally:
                    with original.meta:original.inflight-=1
            return original_call(payload,timeout,job)
        original.call=call
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'screen'
            with patch.object(m,'verify_case',return_value=dict(verified=True)),patch.object(m,'materialize',side_effect=self.old_trial):
                rows,summary=c.run_screen(backend,self.counter,out,time.monotonic()+1200,None,'a'*64)
                report=c.assemble(out,self.counter,'screen',None,'a'*64)
            self.assertFalse(summary['complete']);self.assertEqual(summary['unknown_usage_calls'],1)
            self.assertEqual(len(original.calls),2);self.assertEqual(len(original.reservations),2)
            self.assertEqual(sum(not r['recorded'] for r in report['rows']),6)
            self.assertEqual(report['independently_replayed'],1);self.assertIsNone(rows[0]['generation_tokens'])


if __name__=='__main__':unittest.main()
