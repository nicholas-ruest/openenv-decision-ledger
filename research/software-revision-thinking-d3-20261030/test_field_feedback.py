import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'research/software-public-check-20261028'))
from field_feedback import mismatches,compact,canonical

class PublicFieldTests(unittest.TestCase):
    def test_reports_nested_field_and_sequence_order(self):
        values=mismatches({'ignored':[False,True]},{'ignored':[True,False]})
        self.assertEqual([x['path'] for x in values],[['ignored',0],['ignored',1]])
    def test_types_are_not_coerced(self):
        self.assertEqual(mismatches(True,1)[0]['kind'],'type')
    def test_keys_lengths_and_output_limit(self):
        self.assertEqual(mismatches({},dict(x=True))[0]['kind'],'missing')
        self.assertEqual(mismatches([1],[1,2])[0]['kind'],'length')
        self.assertEqual(len(mismatches(list(range(128)),[-1]*128,limit=2)),2)
    def test_identical_values_have_no_diagnostic(self):
        self.assertEqual(mismatches({'x':[True,None]},{'x':[True,None]}),[])
    def test_public_scope_and_unchanged_rejection(self):
        with self.assertRaises(ValueError):compact(dict(public_only=False,hidden_access=True))
        value=dict(kind='candidate_rejected',public_only=True,hidden_access=False)
        self.assertEqual(compact(value),value)
    def test_compact_preserves_flags_without_args_or_hidden_data(self):
        value=dict(kind='public_example_check',public_only=True,hidden_access=False,passed=0,total=6,
                   execution_errors=0,tests=[dict(test=i,passed=False,error_type=None) for i in range(1,7)],
                   first_failures=[dict(test=i,args=['public-only'],expected={'x':'a'*500},actual={'x':'b'*500},error_type=None) for i in (1,2)])
        result=compact(value)
        self.assertEqual(result['passed'],0);self.assertEqual(len(result['tests']),6)
        self.assertNotIn('args',canonical(result));self.assertLessEqual(len(canonical(result).encode()),600)
        self.assertTrue(result['field_mismatches'])

if __name__=='__main__':unittest.main()
