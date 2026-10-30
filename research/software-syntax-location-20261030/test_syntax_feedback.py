from caller import modules
modules()
import copy,json,unittest
from syntax_feedback import augment
from syntax_review import SyntaxReviewEnvironment,ProposalAction
from repair_env.tasks import make_task
class SyntaxFeedbackTests(unittest.TestCase):
 def setUp(self):
  self.review=dict(kind='candidate_rejected',public_only=True,hidden_access=False)
 def test_actual_parser_location_and_no_source_echo(self):
  source='def broken(:\n    return 1\n'
  result=augment(self.review,source)
  self.assertEqual(result['syntax_error']['line'],1)
  self.assertGreater(result['syntax_error']['offset'],0)
  self.assertEqual(result['diagnostic_scope'],'submitted_source_only')
  self.assertNotIn('text',result['syntax_error']);self.assertNotIn(source,json.dumps(result))
  self.assertNotIn('syntax_error',self.review)
 def test_valid_and_nonparse_rejected_source_unchanged(self):
  self.assertEqual(augment(self.review,'x = 1'),self.review)
  self.assertEqual(augment(self.review,'lambda x: x'),self.review)
 def test_only_rejected_public_source_admitted(self):
  good=dict(self.review,kind='public_field_check')
  self.assertEqual(augment(good,'def broken(:'),good)
  for bad in [dict(self.review,public_only=False),dict(self.review,hidden_access=True)]:
   with self.assertRaises(ValueError):augment(bad,'def broken(:')
  for source in [None,'a'*8193]:
   with self.assertRaises(ValueError):augment(self.review,source)
 def test_real_native_arms_same_first_prompt_and_syntax_exposure(self):
  initial=[];reviews=[]
  for arm in ['standard_review','syntax_review']:
   env=SyntaxReviewEnvironment(arm=arm);initial.append(env.reset(seed=2880000,task_id='software_repair-ignore-d2').model_dump())
   review=env.step(ProposalAction(content='def classify_ignore(:\n    return {}\n'))
   self.assertFalse(review.done);self.assertEqual(review.reward,0)
   reviews.append(json.loads(review.feedback))
   task=make_task('software_repair-ignore-d2',2880000)
   final=env.step(ProposalAction(content=task.reference_source))
   self.assertTrue(final.done);self.assertEqual(final.reward,1)
  self.assertEqual(initial[0],initial[1])
  self.assertNotIn('syntax_error',reviews[0])
  self.assertEqual(reviews[1]['syntax_error']['line'],1)
  changed=copy.deepcopy(reviews[1]);changed.pop('syntax_error');changed.pop('diagnostic_scope')
  self.assertEqual(reviews[0],changed)
