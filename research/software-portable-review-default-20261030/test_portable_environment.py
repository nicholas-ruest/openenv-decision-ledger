"""Native finalization contract checks; no provider or model calls."""
import unittest
from portable_environment import PortableReviewEnvironment,ProposalAction
from repair_env.direct_environment import DirectRepairEnvironment
from repair_env.environment import RepairAction
from repair_env.tasks import make_task

TASK='software_repair-ignore-d3'
SEED=2940000
class FinishContractTests(unittest.TestCase):
 def test_empty_finish_from_reset_is_terminal_with_actual_native_reward(self):
  direct=DirectRepairEnvironment();direct.reset(task_id=TASK,seed=SEED)
  expected=direct._core.step(RepairAction(op='submit')).reward
  for arm in ['neutral_review','public_review']:
   env=PortableReviewEnvironment(arm=arm);env.reset(task_id=TASK,seed=SEED)
   final=env.step(ProposalAction())
   self.assertTrue(final.done);self.assertEqual(final.reward,expected)
   self.assertEqual(final.remaining_responses,0)
 def test_finish_after_reference_proposal_keeps_module_and_is_idempotent(self):
  task=make_task(TASK,SEED)
  env=PortableReviewEnvironment(arm='public_review');env.reset(task_id=TASK,seed=SEED)
  review=env.step(ProposalAction(content=task.reference_source))
  self.assertFalse(review.done);self.assertEqual(review.reward,0)
  final=env.step(ProposalAction());self.assertTrue(final.done);self.assertEqual(final.reward,1)
  self.assertEqual(env.step(ProposalAction()).model_dump(),final.model_dump())
 def test_two_nonempty_reference_actions_and_identical_first_observations(self):
  task=make_task(TASK,SEED);initial=[]
  for arm in ['neutral_review','public_review']:
   env=PortableReviewEnvironment(arm=arm);initial.append(env.reset(task_id=TASK,seed=SEED).model_dump())
   review=env.step(ProposalAction(content=task.reference_source))
   self.assertFalse(review.done);self.assertEqual(review.reward,0)
   final=env.step(ProposalAction(content=task.reference_source))
   self.assertTrue(final.done);self.assertEqual(final.reward,1)
  self.assertEqual(initial[0],initial[1])
  self.assertIn('Empty content ends the episode at any point',initial[0]['prompt'])
 def test_action_schema_does_not_add_actor_or_sampler_knobs(self):
  schema=ProposalAction.model_json_schema()
  self.assertEqual(schema['properties']['content']['maxLength'],8192)
  for key in ['submit','enable_thinking','chat_template_kwargs','sampler']:
   self.assertNotIn(key,schema['properties'])
