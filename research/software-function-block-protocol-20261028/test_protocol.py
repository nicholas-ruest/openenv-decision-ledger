import unittest
from protocol import capture,schedule,ARMS,SEEDS,TARGETS,SAMPLING

class ProtocolTests(unittest.TestCase):
    def test_identical_problems_with_explicit_schema_instruction_treatment(self):
        for task in TARGETS:
            a=capture(task,SEEDS['screen'][0],ARMS[0]);b=capture(task,SEEDS['screen'][0],ARMS[1])
            self.assertEqual(a['problem'],b['problem']);self.assertEqual(a['problem_sha256'],b['problem_sha256'])
            self.assertNotEqual(a['schema'],b['schema']);self.assertNotEqual(a['prompt_sha256'],b['prompt_sha256'])
            for row in [a,b]:
                self.assertEqual({k:v for k,v in row['request'].items() if k!='messages'},SAMPLING)
            self.assertNotIn('mode',a['schema']['properties']);self.assertIn('mode',b['schema']['properties'])
    def test_no_added_example_feedback_or_hidden_fields(self):
        for arm in ARMS:
            a=capture(next(iter(TARGETS)),SEEDS['screen'][0],arm)
            self.assertNotIn('feedback',a['problem']);self.assertNotIn('hidden',a['problem'])
            self.assertEqual(a['problem']['reward'],0);self.assertFalse(a['problem']['done'])
    def test_disjoint_ids_seeds_and_counterbalanced_order(self):
        s=schedule('screen','unit');c=schedule('confirmation','unit')
        self.assertEqual(len(s),32);self.assertEqual(len({r['attempt_id'] for r in s+c}),64)
        self.assertFalse({r['seed'] for r in s}&{r['seed'] for r in c})
        self.assertEqual([r['arm'] for r in s[:2]],list(ARMS));self.assertEqual([r['arm'] for r in s[8:10]],list(reversed(ARMS)))
    def test_no_undeclared_arm_phase_or_silent_namespace(self):
        with self.assertRaises(ValueError):capture(next(iter(TARGETS)),1,'other')
        with self.assertRaises(ValueError):schedule('screen','')
        with self.assertRaises(ValueError):schedule('other','unit')

if __name__=='__main__':unittest.main()
