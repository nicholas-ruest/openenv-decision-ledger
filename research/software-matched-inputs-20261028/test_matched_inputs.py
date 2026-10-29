import json
import unittest
from matched_inputs import Trial,jobs

class InputTests(unittest.TestCase):
    def pair(self):
        a=jobs('screen','unit-fixture')[0];b=dict(a,arm='public_check');a=dict(a,arm='review_control')
        return Trial(a),Trial(b)
    def test_first_prompts_identical_and_only_intermediate_feedback_differs(self):
        a,b=self.pair();self.assertEqual(a.messages,b.messages)
        wrong=json.dumps({'content':a.env._direct._task.initial_source})
        self.assertFalse(a.consume(wrong)['done']);self.assertFalse(b.consume(wrong)['done'])
        x,y=a.native[-1].copy(),b.native[-1].copy()
        self.assertNotEqual(x.pop('feedback'),y.pop('feedback'));self.assertEqual(x,y)
        self.assertNotIn('passed',a.messages[-1]['content']);self.assertIn('passed',b.messages[-1]['content'])
    def test_invalid_first_reply_is_terminal_in_both_arms_without_substitution(self):
        for reply in ['not json','{"answer":"x"}','{"submit":"false"}']:
            for t in self.pair():
                self.assertEqual(t.consume(reply)['category'],'format')
                self.assertEqual(t.native,[])
                with self.assertRaises(ValueError):t.consume('{}')
    def test_valid_rejected_code_may_revise_with_same_native_grader(self):
        for t in self.pair():
            r=t.consume(json.dumps({'content':'import os\ndef classify_ignore(a,b): return os.environ'}))
            self.assertFalse(r['done']);self.assertEqual(r['native_reward'],0)
            r=t.consume(json.dumps({'content':t.env._direct._task.reference_source}))
            self.assertEqual(r['category'],'full');self.assertEqual(r['native_reward'],1)
    def test_early_submit_finishes_without_a_second_generation(self):
        for t in self.pair():
            self.assertEqual(t.consume('{"submit":true}')['category'],'wrong')
            with self.assertRaises(ValueError):t.consume('{}')
    def test_fresh_phase_identity_and_counterbalanced_arm_order(self):
        s=jobs('screen','unit-fixture');c=jobs('confirmation','unit-fixture')
        self.assertEqual(len(s),32);self.assertEqual(len({r['attempt_id'] for r in s+c}),64)
        self.assertFalse({r['seed'] for r in s}&{r['seed'] for r in c})
        self.assertEqual([r['arm'] for r in s[:2]],['review_control','public_check'])
        self.assertEqual([r['arm'] for r in s[8:10]],['public_check','review_control'])
        self.assertNotEqual(s[0]['attempt_id'],jobs('screen','other-fresh-archive')[0]['attempt_id'])

if __name__=='__main__':unittest.main()
