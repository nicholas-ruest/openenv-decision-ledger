"""Native advice exposure and unchanged grading; no model calls."""
import json,unittest
from caller import modules
protocol,Trial=modules()
from retention_environment import RetentionEnvironment
from mandatory_environment import ProposalAction
from repair_env.tasks import make_task,SOURCE_PATH
TASK='software_repair-ignore-d3'
SEED=2940000
class RetentionTests(unittest.TestCase):
 def test_identical_reset_and_only_treatment_advice_after_public_pass(self):
  ref=make_task(TASK,SEED).reference_source;initial=[];reviews=[]
  for arm in ('standard_review','retain_review'):
   env=RetentionEnvironment(arm=arm);initial.append(env.reset(task_id=TASK,seed=SEED).model_dump())
   ops=[];core=env._direct._core;original=core.step
   def tracked(action,*args,**kwargs):
    ops.append(action.op);return original(action,*args,**kwargs)
   core.step=tracked
   obs=env.step(ProposalAction(content=ref));self.assertFalse(obs.done);self.assertEqual(obs.reward,0)
   self.assertEqual(ops,['write'])
   review=json.loads(obs.feedback);reviews.append(review)
   self.assertEqual(review['passed'],review['total']);self.assertEqual(review['total'],6)
   self.assertTrue(review['public_only']);self.assertFalse(review['hidden_access'])
   self.assertEqual(env._direct._files[SOURCE_PATH],ref)
   final=env.step(ProposalAction());self.assertTrue(final.done);self.assertEqual(final.reward,1)
  self.assertEqual(initial[0],initial[1])
  self.assertNotIn('retention_advice',reviews[0]);self.assertTrue(reviews[1]['retention_advice'])
  self.assertIn('does not prove the full contract',reviews[1]['review_advice'])
  for key in ('kind','public_only','hidden_access','passed','total','contract_reminder','field_mismatches'):
   self.assertEqual(reviews[0].get(key),reviews[1].get(key))
 def test_failing_examples_never_trigger_retention_advice(self):
  for arm in ('standard_review','retain_review'):
   env=RetentionEnvironment(arm=arm);reset=env.reset(task_id=TASK,seed=SEED)
   obs=env.step(ProposalAction(content=reset.source))
   review=json.loads(obs.feedback);self.assertNotIn('retention_advice',review)
   self.assertLess(review.get('passed',0),review.get('total',6))
 def test_rejected_proposal_gets_no_retention_advice(self):
  env=RetentionEnvironment(arm='retain_review');env.reset(task_id=TASK,seed=SEED)
  obs=env.step(ProposalAction(content='import os'))
  self.assertFalse(obs.done);self.assertEqual(obs.reward,0)
  self.assertNotIn('retention_advice',json.loads(obs.feedback))
 def test_invalid_arm_fails_closed(self):
  with self.assertRaises(ValueError):RetentionEnvironment(arm='other')
if __name__=='__main__':unittest.main()
