"""Confirmation gates only. Never construct the reserved Native case in tests."""
import ast
import copy
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import confirm_protocol as protocol
sys.path.insert(0,str(Path(__file__).resolve().parent))
import caller

def fictional_selection():
    return dict(screen_source=protocol.SCREEN_SOURCE,screen_inputs_sha256=protocol.SCREEN_INPUTS,
        screen_selection_passed=True,all_live_replies_verified=True,assigned=8,unknown_usage=0,
        actual_calls=16,full_rate_delta=.25,semantic_mean_delta=.1,profile_sha256=protocol.digest(protocol.profile()),
        response_ids=[hashlib.sha256(('fictional-'+str(i)).encode()).hexdigest() for i in range(16)],
        screen_problem_sha256='a'*64,screen_assessment_sha256='b'*64,
        screen_raw_events_sha256=['c'*64]*4,screen_records_sha256=['d'*64]*4)

class ConfirmationGates(unittest.TestCase):
    def setUp(self):protocol._CHOICE=None
    def tearDown(self):protocol._CHOICE=None
    def test_import_and_missing_selection_never_capture_reserved_case(self):
        with patch.object(protocol,'Trial',side_effect=AssertionError('reserved Native case materialized')) as trial:
            with self.assertRaises(ValueError):protocol.bundle(0)
            with self.assertRaises(ValueError):protocol.capture(protocol.schedule('confirmation')[0])
            trial.assert_not_called()
    def test_positive_selection_receipt_is_exact_bound_and_defensively_copied(self):
        value=fictional_selection();chosen=protocol.selection(value);chosen['response_ids'].clear()
        self.assertEqual(len(value['response_ids']),16)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'fictional-selection';path.write_text(json.dumps(value));digest=hashlib.sha256(path.read_bytes()).hexdigest()
            protocol.configure(path,digest);self.assertEqual(protocol.choice(),value)
            with self.assertRaises(ValueError):protocol.configure(path,'0'*64)
            path.write_text('{}')
            with self.assertRaises(ValueError):protocol.configure(path,digest)
    def test_incomplete_unknown_nonpositive_or_wrong_profile_selection_denied(self):
        mutations=[lambda v:v.update(assigned=7),lambda v:v.update(unknown_usage=1),
            lambda v:v.update(full_rate_delta=0),lambda v:v.update(semantic_mean_delta=-.01),
            lambda v:v.update(screen_source='0'*40),lambda v:v.update(profile_sha256='0'*64),
            lambda v:v.update(screen_selection_passed=False),lambda v:v.update(all_live_replies_verified=False),
            lambda v:v['response_ids'].__setitem__(1,v['response_ids'][0]),
            lambda v:v['screen_inputs_sha256'].__setitem__(0,'0'*64)]
        for mutate in mutations:
            value=copy.deepcopy(fictional_selection());mutate(value)
            with self.assertRaises(ValueError):protocol.selection(value)
    def test_unchanged_trial_and_frozen_disjoint_assignments_without_observations(self):
        self.assertIs(protocol.Trial,protocol.original.Trial)
        self.assertEqual(protocol.schedule('confirmation'),protocol.original.schedule('confirmation'))
        self.assertEqual(len({j['attempt_id'] for j in protocol.schedule('confirmation')}),8)
        self.assertTrue(all(j['seed']==2730000 for j in protocol.schedule('confirmation')))
        with self.assertRaises(ValueError):protocol.schedule('screen')
        self.assertEqual(protocol.profile()['completion_with_observations'],8192)
        self.assertEqual(protocol.profile()['context'],24576)
    def test_paid_loop_route_accounting_and_reconciliation_code_are_unchanged(self):
        base=caller.ROOT/'research/software-source-diagnostics-off8k-20261029/caller.py'
        source=base.read_text();tree=ast.parse(source)
        for name in ['phase','LiveBackend','reconciliation','record']:
            node=next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
            self.assertEqual(inspect.getsource(getattr(caller,name)).strip(),ast.get_source_segment(source,node).strip())
    def test_real_cli_invalid_selection_fails_under_supervisor_before_capture(self):
        source=subprocess.check_output(['git','-C',str(caller.ROOT),'rev-parse','HEAD'],text=True).strip()
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);out=tmp/'live';selection=tmp/'invalid-selection';selection.write_text('{}');inputs=tmp/'inputs';inputs.write_text('{}')
            args=[sys.executable,str(Path(caller.__file__)),'--execute','--selection',str(selection),'--selection-sha256',hashlib.sha256(selection.read_bytes()).hexdigest(),'--expected-source',source,'--inputs',str(inputs),'--inputs-sha256','0'*64,'--receipt',str(tmp/'receipt'),'--reconciliation',str(tmp/'missing-audit'),'--tokenizer','/home/ruv/arena-tokenizer.json','--output',str(out),'--amendment-sha256','0'*64]
            subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=20)
            self.assertFalse(out.exists())
            events=[json.loads(x) for x in out.with_suffix('.supervision.jsonl').read_text().splitlines()]
            self.assertEqual(events[-1]['status'],'worker_failed');self.assertTrue(events[-1]['shutdown_verified'])

if __name__=='__main__':unittest.main()
