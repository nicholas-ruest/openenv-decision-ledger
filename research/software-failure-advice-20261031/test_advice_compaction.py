import os
import unittest
from compare_advice_tokens import compare,load_counter


class CompactionTests(unittest.TestCase):
    def test_shorter_note_changes_only_receipt_and_counts_actual_wire_tokens(self):
        result=compare(load_counter(os.environ['HELPER_TEST_TOKENIZER']))
        self.assertGreater(result['saved_tokens'],0)
        self.assertTrue(result['first_prompts_identical']);self.assertTrue(result['native_review_identical'])
        self.assertEqual(result['model_calls'],0);self.assertFalse(result['model_improvement'])


if __name__=='__main__':unittest.main()
