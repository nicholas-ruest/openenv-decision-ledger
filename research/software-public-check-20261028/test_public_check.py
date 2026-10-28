import copy
import unittest
from public_check import feedback,revision_message,examples_from_reset

class Program:
    def __init__(self,source):self.source=source
    def run(self,name,args):
        if self.source=='error':raise ValueError('private message')
        if self.source=='mutate':args.clear();return 1
        return 1 if self.source=='correct' else 0

class PublicCheckTests(unittest.TestCase):
    def setUp(self):self.reset={'examples':repr([([1],1)]*6),'hidden':'must never inspect'}
    def test_all_public_matches(self):
        r=feedback(self.reset,'correct',Program);self.assertEqual(r['passed'],6);self.assertFalse(r['hidden_access'])
    def test_valid_wrong_distinct_from_execution(self):
        wrong=feedback(self.reset,'wrong',Program);bad=feedback(self.reset,'error',Program)
        self.assertEqual(wrong['passed'],0);self.assertEqual(wrong['execution_errors'],0);self.assertEqual(bad['execution_errors'],6)
        self.assertNotIn('private message',str(bad));self.assertEqual(len(wrong['first_failures']),2)
    def test_original_reset_not_mutated(self):
        original=copy.deepcopy(self.reset);feedback(self.reset,'mutate',Program);self.assertEqual(self.reset,original)
    def test_public_examples_are_not_executed_as_host_code(self):
        for value in ['__import__("os").getcwd()',repr([([1],1)]*7),'x'*32769]:
            with self.assertRaises((ValueError,SyntaxError)):examples_from_reset({'examples':value})
    def test_compile_rejection_separate(self):
        def reject(_):raise RuntimeError('private text')
        r=feedback(self.reset,'source',reject);self.assertEqual(r['kind'],'candidate_rejected');self.assertNotIn('private text',str(r))
    def test_type_sensitive_public_grading(self):
        self.reset['examples']=repr([([1],True)]*6);self.assertEqual(feedback(self.reset,'correct',Program)['passed'],0)
    def test_control_does_not_receive_feedback_and_no_preserve_guidance(self):
        r=feedback(self.reset,'wrong',Program);control=revision_message('review_control',r);variant=revision_message('public_check',r)
        self.assertNotIn('first_failures',control);self.assertIn('first_failures',variant);self.assertNotIn('preserv',variant)
        with self.assertRaises(ValueError):revision_message('public_check',{'public_only':False})

if __name__=='__main__':unittest.main()
