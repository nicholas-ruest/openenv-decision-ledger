import copy
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import entry_case as m
import matched_protocol as p
import finite_caller as c
import guarded_transport as b
import live_screen
import assess_screen
import test_finite_caller as fixture


class LiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.FiniteTests.setUpClass();cls.counter=fixture.FiniteTests.counter
        cls.responses={new['attempt_id']:copy.deepcopy(fixture.FiniteTests.responses[old['attempt_id']]) for new,old in zip(p.jobs('screen'),p.jobs('qualification'))}

    def old_trial(self,job,*args):
        old=next(x for x in p.jobs('qualification') if x['sample']==job['sample'] and x['arm']==job['arm'])
        return p.Trial(old)

    def test_unsealed_guard_refuses_before_private_source_backend_or_case_reads(self):
        with patch.object(m,'sha',side_effect=AssertionError('no private read')):
            for phase in ('screen','confirmation'):
                with self.assertRaises(ValueError):m.materialize(p.jobs(phase)[0],Path('unused'),'a'*64)
        with patch.object(b,'load',side_effect=AssertionError('no backend load')):
            with self.assertRaises(ValueError):b.guarded_backend(SimpleNamespace())
        with patch.object(b,'verify_clean_source',side_effect=AssertionError('no source read')):
            with self.assertRaises(ValueError):live_screen.require_supervision(SimpleNamespace(case_audit=None,case_audit_sha256=None))

    def test_guarded_backend_delegates_existing_arguments_after_gate_and_source_checks(self):
        captured=[]
        class Original:
            scripted=False
            def __init__(self,*args):self.counter=LiveTests.counter;captured.append(args)
        args=SimpleNamespace(case_audit=Path('private-audit'),case_audit_sha256='a'*64,expected_source='b'*40,
            receipt=Path('existing-receipt'),reconciliation=Path('fresh-audit'),tokenizer=Path('existing-tokenizer'),amendment_sha256='c'*64)
        with patch.object(m,'verify_case',return_value=dict(verified=True)),patch.object(b,'verify_clean_source') as source,patch.object(b,'load',return_value=SimpleNamespace(LiveBackend=Original)):
            backend=b.guarded_backend(args)
        source.assert_called_once_with(args.expected_source)
        self.assertEqual(captured,[(args.receipt,args.reconciliation,args.tokenizer,args.amendment_sha256)])
        self.assertFalse(backend.scripted);self.assertEqual(backend.phase,'screen')

    def test_complete_latest_anchor_chain_is_source_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);old=m.prior();base=old._prior();pairs=[['software_repair-ignore-d3',2560000]];parent=None;parent_sha=None
            for i,(kind,task,seed,hashes) in enumerate([('failure-advice-case-audit','software_repair-ignore-d2',3160000,None),('preserve-first-case-audit','software_repair-ignore-d3',3180000,base.method_hashes),('top-level-note-case-audit','software_repair-ignore-d3',3200000,old.method_hashes),('entry-order-review-case-audit','software_repair-ignore-d3',3220000,m.method_hashes)]):
                value=dict(kind=kind,task_id=task,new_seed=seed,prior_task_seed_pairs=pairs,prior_inventory_sha256=p.digest(pairs))
                if hashes:value['method_sha256']=hashes()
                if parent:value.update(parent_audit_path=str(parent),parent_audit_sha256=parent_sha)
                path=root/(str(i)+'.json');path.write_text(json.dumps(value));parent=path;parent_sha=m.sha(path);pairs=sorted(pairs+[[task,seed]])
            with patch.object(m,'CASE_AUDIT_SHA256',parent_sha),patch.object(base,'verify_inventory',return_value=dict(verified=True,input_overlap=0)) as check:
                self.assertTrue(m.verify_case(p.jobs('screen')[0],parent,parent_sha)['verified']);self.assertEqual(check.call_count,4)
                parent.write_text('{}')
                with self.assertRaises(ValueError):m.verify_case(p.jobs('screen')[0],parent,parent_sha)

    def test_screen_adapter_matches_actual_old_qualification_messages_and_grade(self):
        with patch.object(m,'verify_case',return_value=dict(verified=True)):
            for job in p.jobs('qualification')[:2]:
                a=p.Trial(job);z=m.ScreenTrial(job,None,None);self.assertEqual(a.messages,z.messages)
                code=fixture.fixture.MatchedTests.fixture.good
                message=dict(role='assistant',content=json.dumps(dict(content=code)))
                self.assertEqual(a.consume(message,'stop'),z.consume(message,'stop'))
                self.assertEqual(a.consume(dict(role='assistant',content='{"content":""}'),'stop'),z.consume(dict(role='assistant',content='{"content":""}'),'stop'))

    def test_mock_live_archives_require_original_successful_supervisor(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(m,'verify_case',return_value=dict(verified=True)),patch.object(m,'materialize',side_effect=self.old_trial):
            out=Path(tmp)/'screen';original=fixture.Backend(self.counter,self.responses);original.scripted=False
            call=original.call
            original.call=lambda payload,timeout,job:call(payload,timeout,job,len([x for x in original.calls if x[0]==job['attempt_id']]))
            rows,summary=c.run_screen(b.AtomicDelegation(original),self.counter,out,time.monotonic()+1200,None,'a'*64)
            self.assertTrue(summary['complete']);self.assertFalse(summary['scripted']);self.assertEqual(len(original.calls),16)
            self.assertFalse(assess_screen.assess(out,self.counter,None,'a'*64)['fitness_computed'])
            receipt=out.with_suffix('.supervision.jsonl')
            binding=dict(worker_pid=77,parent_pid=76,deadline=time.monotonic()+1200,source='a'*40,case_audit_sha256='a'*64,archive=str(out.resolve()))
            (out/'supervision-binding.json').write_text(json.dumps(binding))
            events=[dict(event='starting',target='execute_phase',wall_seconds=1200),dict(event='started',pid=77),dict(event='terminal',pid=77,status='completed',worker_exitcode=0,shutdown_verified=True,finished_before_deadline=True)]
            receipt.write_text(''.join(json.dumps(e)+'\n' for e in events))
            with patch.object(b,'verify_clean_source',return_value=None):score=assess_screen.assess(out,self.counter,None,'a'*64)
            self.assertEqual(score['actual_module'],'fitness.mjs:scoreCell');self.assertFalse(score['selection_passed'])
            self.assertEqual([x['computed_relation_exposures'] for x in score['groups']],[0,4])
            events[-1]['pid']=78;receipt.write_text(''.join(json.dumps(e)+'\n' for e in events))
            self.assertFalse(assess_screen.assess(out,self.counter,None,'a'*64)['fitness_computed'])
            path=next(out.glob('*/trace.json'));trace=json.loads(path.read_text());trace['execution_sha256']['finite_caller.py']='f'*64;path.write_text(json.dumps(trace))
            with self.assertRaises(ValueError):c.assemble(out,self.counter,'screen',None,'a'*64)

    def test_mock_live_second_unknown_stops_new_pairs_and_retains_known_prefix(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(m,'verify_case',return_value=dict(verified=True)),patch.object(m,'materialize',side_effect=self.old_trial):
            out=Path(tmp)/'screen';original=fixture.Backend(self.counter,self.responses);original.scripted=False;call=original.call
            def unknown(payload,timeout,job,turn):
                value=call(payload,timeout,job,turn)
                if job==p.jobs('screen')[0] and turn==1:raise TimeoutError('synthetic unknown second')
                return value
            original.call=lambda payload,timeout,job:unknown(payload,timeout,job,0 if len([x for x in original.calls if x[0]==job['attempt_id']])==0 else 1)
            rows,summary=c.run_screen(b.AtomicDelegation(original),self.counter,out,time.monotonic()+1200,None,'a'*64)
            self.assertFalse(summary['complete']);self.assertEqual(summary['unknown_usage_calls'],1)
            self.assertGreater(rows[0]['known_generation_tokens'],0);self.assertIsNone(rows[0]['generation_tokens']);self.assertEqual(len(original.calls),4)
            self.assertEqual(sum(not x['recorded'] for x in c.assemble(out,self.counter,'screen',None,'a'*64)['rows']),6)


if __name__=='__main__':unittest.main()
