import unittest
from software_quote import quote

PLAN=dict(attempts_per_phase=32,max_model_calls_per_attempt=2,max_model_calls_per_phase=64,max_retries=0,
          first_call_generation_max=2048,completion_budget_including_postreset_observations=4096,context_budget=8192)
class QuoteTests(unittest.TestCase):
    def test_complete_shared_output_budget_and_no_authority(self):
        r=quote(PLAN,{'input':'.2','output':'2.5'},'1')
        self.assertEqual(r['complete_phase_quote_usd'],'0.47579136')
        self.assertEqual(r['generation_token_bound'],131072)
        self.assertFalse(r['execution_authorized']);self.assertFalse(r['reservation_performed'])
    def test_insufficient_remaining_does_not_shrink_or_reuse_calls(self):
        # Fictional remaining-allocation fixture, not account evidence.
        r=quote(PLAN,{'input':'.2','output':'2.5'},'.10')
        self.assertFalse(r['budget_feasible']);self.assertEqual(r['calls_bound'],64)
    def test_changed_phase_or_nonfinite_amount_is_refused(self):
        with self.assertRaises(ValueError):quote(dict(PLAN,max_model_calls_per_phase=32),{'input':1,'output':1},1)
        for value in ['NaN','-1','Infinity']:
            with self.assertRaises(ValueError):quote(PLAN,{'input':value,'output':1},1)

if __name__=='__main__':unittest.main()
