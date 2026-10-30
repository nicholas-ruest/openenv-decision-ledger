"""Native checks for declared early finish; no provider calls."""
import json,unittest
from caller import modules
from repair_env.tasks import make_task
protocol,Trial=modules()
class PortableTrialTests(unittest.TestCase):
 def test_empty_action_is_terminal_on_first_turn(self):
  for job in protocol.schedule('screen')[:2]:
   trial=Trial(job);r=trial.consume('{}')
   self.assertTrue(r['done']);self.assertTrue(trial.closed);self.assertEqual(r['native_reward'],0)
   self.assertEqual(trial.turn,1)
   with self.assertRaises(ValueError):trial.consume('{}')
 def test_nonempty_proposal_review_then_empty_retains_reference(self):
  for job in protocol.schedule('screen')[:2]:
   trial=Trial(job);ref=make_task(job['task_id'],job['seed']).reference_source
   review=trial.consume(json.dumps(dict(content=ref)))
   self.assertFalse(review['done']);self.assertEqual(review['native_reward'],0)
   final=trial.consume('{}')
   self.assertTrue(final['done']);self.assertEqual(final['semantic_reward'],1)
   self.assertTrue(trial.closed)
if __name__=='__main__':unittest.main()
