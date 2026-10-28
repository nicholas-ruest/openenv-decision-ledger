import json
import unittest
from matched_inputs import Trial,jobs

class TerminalTests(unittest.TestCase):
    def trial(self):return Trial(jobs('screen','terminal-unit')[0])
    def test_compile_rejected_final_is_execution_even_when_native_error_empty(self):
        t=self.trial();r=t.consume(json.dumps({'content':'import os','submit':True}))
        self.assertEqual(t.native[-1]['error'],'')
        self.assertEqual(r['category'],'execution');self.assertTrue(r['compile_rejected'])
        self.assertEqual(r['native_reward'],0);self.assertIsNone(r['semantic_reward'])
    def test_runtime_failure_and_valid_wrong_are_separate(self):
        t=self.trial();r=t.consume(json.dumps({'content':'def classify_ignore(a,b):\n    return 1//0','submit':True}))
        self.assertEqual(r['category'],'execution');self.assertGreater(r['hidden_execution_errors'],0)
        t=self.trial();r=t.consume('{"submit":true}')
        self.assertEqual(r['category'],'wrong');self.assertEqual(r['hidden_execution_errors'],0)
    def test_private_analysis_never_changes_native_messages(self):
        t=self.trial();ref=t.env._direct._task.reference_source
        r=t.consume(json.dumps({'content':ref,'submit':True}))
        self.assertEqual(r['category'],'full');self.assertEqual(r['semantic_reward'],1)
        for m in t.messages:
            self.assertNotIn('hidden_execution_errors',m['content'])
            self.assertNotIn('compile_rejected',m['content'])
        self.assertEqual(json.loads(t.messages[-1]['content']),t.native[-1])
    def test_external_provider_and_budget_failures_are_terminal(self):
        for category in ['provider','budget','execution']:
            t=self.trial();t.consume('{}');r=t.abort(category)
            self.assertEqual(r['category'],category);self.assertIsNone(r['semantic_reward'])
            with self.assertRaises(ValueError):t.consume('{}')
        with self.assertRaises(ValueError):self.trial().abort('full')

if __name__=='__main__':unittest.main()
