import json
import unittest
from unittest.mock import patch
from revision_environment import RevisionEnvironment,RevisionAction,TASKS
from repair_env import environment

class RevisionTests(unittest.TestCase):
    def env(self,arm='public_check',task=TASKS[0],seed=2340000):
        e=RevisionEnvironment(arm=arm);o=e.reset(task_id=task,seed=seed);return e,o
    def test_first_reset_identical_between_arms(self):
        a,oa=self.env();b,ob=self.env('review_control');self.assertEqual(oa.model_dump(),ob.model_dump());self.assertEqual(a._direct._files,b._direct._files)
    def test_reference_two_response_path_and_terminal_idempotence(self):
        for task in TASKS:
            e,o=self.env(task=task);source=e._direct._task.reference_source
            first=e.step(RevisionAction(content=source));self.assertFalse(first.done);self.assertEqual(first.reward,0)
            self.assertEqual(json.loads(first.feedback)['passed'],6)
            final=e.step(RevisionAction(submit=True));self.assertTrue(final.done);self.assertEqual(final.reward,1)
            self.assertEqual(e.step(RevisionAction(content=o.source)),final);self.assertEqual(e.state.step_count,2)
    def test_no_hidden_check_on_proposal(self):
        e,o=self.env();original=environment.check
        with patch.object(environment,'check',wraps=original) as check:
            first=e.step(RevisionAction(content=o.source));self.assertFalse(first.done)
            self.assertEqual(check.call_count,0)
    def test_wrong_then_reference_repair_receives_native_grade(self):
        e,o=self.env();first=e.step(RevisionAction(content=o.source));self.assertLess(json.loads(first.feedback)['passed'],6)
        final=e.step(RevisionAction(content=e._direct._task.reference_source));self.assertEqual(final.reward,1);self.assertTrue(final.done)
    def test_compile_error_can_be_revised_without_host_execution(self):
        e,o=self.env();first=e.step(RevisionAction(content='import os\ndef classify_ignore(a,b): return os.environ'))
        self.assertEqual(json.loads(first.feedback)['kind'],'candidate_rejected');self.assertEqual(first.reward,0)
        self.assertEqual(e.step(RevisionAction(content=e._direct._task.reference_source)).reward,1)
    def test_early_finish_and_unchanged_code_zero(self):
        e,o=self.env();self.assertEqual(e.step(RevisionAction(submit=True)).reward,0)
        e.reset(task_id=TASKS[0],seed=2340001);e.step(RevisionAction(content=o.source));self.assertTrue(e.step(RevisionAction()).done)
    def test_bad_final_write_cannot_grade_previous_reference_as_full(self):
        e,o=self.env();e.step(RevisionAction(content=e._direct._task.reference_source))
        final=e.step(RevisionAction(content='é'*5000));self.assertEqual(final.reward,0);self.assertTrue(final.error)
    def test_neutral_review_omits_computed_results(self):
        e,o=self.env('review_control');r=e.step(RevisionAction(content=o.source));self.assertNotIn('passed',r.feedback);self.assertFalse(r.done)
    def test_reset_clears_previous_terminal_and_task_scope(self):
        e,o=self.env();e.step(RevisionAction(submit=True));r=e.reset(task_id=TASKS[1],seed=2340001);self.assertFalse(r.done);self.assertEqual(e.state.step_count,0)
        with self.assertRaises(ValueError):e.reset(task_id='software_repair-kv-d2')

if __name__=='__main__':unittest.main()
