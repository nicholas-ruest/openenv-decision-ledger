"""Source-only diagnostic controls. No model calls or reserved confirmation case."""
import copy
import inspect
import json
from pathlib import Path
import ast
import unittest
from caller import ROOT,modules
protocol,_=modules()
from source_diagnostics import augment
from public_check import feedback
from repair_env.runner import Program,Rejected
from repair_env.tasks import make_task

class SourceDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        trial=protocol.Trial(protocol.schedule('screen')[0])
        cls.reset={'examples':json.loads(trial.messages[1]['content'])['examples']}
    def test_actual_keyword_rejection_gets_specific_bounded_public_source_detail(self):
        source='def classify_ignore(ignore_lines, entries):\n    return dict(value=True)\n'
        with self.assertRaises(Rejected):Program(source)
        base=feedback(self.reset,source,Program);before=copy.deepcopy(base)
        result=augment(base,source,Program)
        self.assertEqual(result['kind'],'candidate_rejected');self.assertEqual(result['exception_type'],'Rejected')
        self.assertEqual(result['diagnostic_scope'],'submitted_source_only')
        self.assertEqual(result['source_diagnostics'][0]['syntax_kind'],'keyword')
        self.assertEqual(result['source_diagnostics'][0]['line'],2)
        self.assertIn('positional',result['source_diagnostics'][0]['hint'])
        self.assertEqual(base,before);self.assertLessEqual(len(json.dumps(result).encode()),4096)
    def test_valid_reference_public_checks_are_unchanged_not_promoted(self):
        trial=protocol.Trial(protocol.schedule('screen')[0])
        source=make_task(trial.job['task_id'],trial.job['seed']).reference_source
        base=feedback(self.reset,source,Program)
        self.assertEqual(base['passed'],6);self.assertEqual(augment(base,source,Program),base)
        self.assertNotIn('source_diagnostics',base);self.assertNotIn('hidden_reward',base)
    def test_lambda_and_repeated_keyword_locations_bounded_without_echoing_source(self):
        marker='FICTIONAL_SECRET_NOT_TO_ECHO'
        source='def classify_ignore(a,b):\n    marker='+repr(marker)+'\n'+''.join('    v=dict(x=True)\n' for _ in range(12))+'    return (lambda: 0)()\n'
        base=feedback(self.reset,source,Program);result=augment(base,source,Program)
        self.assertEqual(len(result['source_diagnostics']),8)
        self.assertNotIn(marker,json.dumps(result));self.assertTrue(result['public_only']);self.assertFalse(result['hidden_access'])
        shorter='def classify_ignore(a,b):\n    return (lambda: 0)()\n'
        result=augment(feedback(self.reset,shorter,Program),shorter,Program)
        self.assertEqual(result['source_diagnostics'][0]['syntax_kind'],'Lambda')
    def test_noncompiler_results_unknown_manifest_and_hidden_feedback_remain_closed(self):
        base={'kind':'public_example_check','public_only':True,'hidden_access':False,'passed':0,'total':6}
        self.assertEqual(augment(base,'not parsed because no compiler rejection',Program),base)
        rejected=dict(base,kind='candidate_rejected')
        self.assertEqual(augment(rejected,'',object),rejected)
        with self.assertRaises(ValueError):augment(dict(rejected,hidden_access=True),'',Program)
        with self.assertRaises(ValueError):augment(rejected,'x'*8193,Program)
    def test_same_first_native_prompt_and_only_diagnostic_feedback_differs(self):
        jobs=protocol.bundle(0)['screen_jobs'];trials=[protocol.Trial(j) for j in jobs]
        self.assertEqual(trials[0].messages,trials[1].messages)
        bad='def classify_ignore(a,b):\n    return dict(value=True)\n'
        first=[t.consume(json.dumps(dict(content=bad))) for t in trials]
        self.assertTrue(all(v['native_reward']==0 and not v['done'] for v in first))
        neutral=json.loads(trials[0].native[0]['feedback']);detail=json.loads(trials[1].native[0]['feedback'])
        self.assertNotIn('source_diagnostics',neutral);self.assertIn('source_diagnostics',detail)
        expected=dict(detail);expected.pop('source_diagnostics');expected.pop('diagnostic_scope')
        self.assertEqual(neutral,expected)
        source=make_task(jobs[0]['task_id'],jobs[0]['seed']).reference_source
        final=[t.consume(json.dumps(dict(content=source))) for t in trials]
        self.assertTrue(all(v['native_reward']==1 and v['done'] for v in final))
    def test_financial_paid_loop_and_reconciliation_code_match_tested_required_review_caller(self):
        import caller
        source=(ROOT/'research/software-mandatory-feedback8k-20261029/caller.py').read_text();tree=ast.parse(source)
        for name in ['phase','LiveBackend','reconciliation','record']:
            node=next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
            self.assertEqual(inspect.getsource(getattr(caller,name)).strip(),ast.get_source_segment(source,node).strip())

if __name__=='__main__':unittest.main()
