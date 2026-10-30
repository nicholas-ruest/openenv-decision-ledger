import unittest
from localized_revision import Replacement,ProposalAction,apply_replacements,LocalizedReviewEnvironment
from repair_env.tasks import make_task
class LocalRevisionTests(unittest.TestCase):
 def test_atomic_exact_transactions(self):
  source='alpha beta'
  self.assertEqual(apply_replacements(source,[Replacement(before='alpha',after='gamma'),Replacement(before='gamma',after='delta')]),'delta beta')
  for before in ('missing','a'):
   with self.assertRaises(ValueError):apply_replacements(source,[Replacement(before='alpha',after='gamma'),Replacement(before=before,after='x')])
  self.assertEqual(source,'alpha beta')
 def test_size_and_strict_schema(self):
  with self.assertRaises(ValueError):apply_replacements('x',[Replacement(before='x',after='a'*8192),Replacement(before='a'*8192,after='a'*8192+'b')])
  self.assertEqual(ProposalAction(content='',submit=True).content,'')
 def test_native_full_fallback_and_patch_same_grade(self):
  task=make_task('software_repair-ignore-d2',2840000)
  initial=[]
  for arm in ('full_module','local_patch'):
   env=LocalizedReviewEnvironment(arm=arm);initial.append(env.reset(task_id=task.task_id,seed=2840000).model_dump())
   review=env.step(ProposalAction(content=task.reference_source))
   self.assertFalse(review.done);self.assertEqual(review.reward,0)
   final=env.step(ProposalAction());self.assertTrue(final.done);self.assertEqual(final.reward,1)
  self.assertEqual(initial[0],initial[1])
 def test_first_patch_and_ambiguous_representation_rejected(self):
  env=LocalizedReviewEnvironment(arm='local_patch');env.reset(seed=2840000,task_id='software_repair-ignore-d2')
  with self.assertRaises(ValueError):env.step(ProposalAction(replacements=[Replacement(before='x',after='y')]))
  with self.assertRaises(ValueError):env.step(ProposalAction(content='x',replacements=[Replacement(before='x',after='y')]))
