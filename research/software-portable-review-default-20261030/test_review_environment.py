"""Actual native controls, not model-performance evidence."""
from caller import modules
protocol,Trial=modules()
import copy,json,unittest
from review_environment import PublicReviewEnvironment
from mandatory_environment import ProposalAction
from repair_env.tasks import make_task

class DefaultReviewTests(unittest.TestCase):
 def test_sampler_never_varies_by_arm_or_turn(self):
  for job in protocol.schedule('screen'):
   for turn in [0,1]:
    self.assertEqual(protocol.sampling_for(job,turn),protocol.SAMPLING)
    self.assertNotIn('chat_template_kwargs',protocol.sampling_for(job,turn))
 def test_actual_same_first_prompt_and_only_review_information_differs(self):
  initial=[];reviews=[]
  task=make_task('software_repair-ignore-d3',2940000)
  for arm in ['neutral_review','public_review']:
   env=PublicReviewEnvironment(arm=arm)
   initial.append(env.reset(seed=2940000,task_id=task.task_id).model_dump())
   obs=env.step(ProposalAction(content=task.reference_source))
   self.assertFalse(obs.done);self.assertEqual(obs.reward,0)
   reviews.append(json.loads(obs.feedback))
   final=env.step(ProposalAction(content=task.reference_source))
   self.assertTrue(final.done);self.assertEqual(final.reward,1)
  self.assertEqual(initial[0],initial[1])
  self.assertEqual(reviews[0]['kind'],'neutral_review')
  self.assertNotIn('passed',reviews[0]);self.assertNotIn('field_mismatches',reviews[0])
  self.assertEqual(reviews[1]['passed'],6)
  for k in ['contract_reminder','review_advice','public_only','hidden_access']:
   self.assertEqual(reviews[0][k],reviews[1][k])
 def test_unknown_arm_rejected(self):
  with self.assertRaises(ValueError):PublicReviewEnvironment(arm='other')
