import importlib.util,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
p=Path(__file__).with_name('revision_environment.py')
spec=importlib.util.spec_from_file_location('final_domain_revision',p)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
from repair_env.direct_environment import DirectRepairEnvironment,DirectRepairAction
from repair_env.tasks import make_task,SOURCE_PATH

class CueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.task=make_task('software_repair-ignore-d3',2560000)
        cls.good=cls.task.reference_source
        cls.extra=cls.good.replace('    return result\n','    result["extra_internal_path"] = False\n    return result\n')

    def environments(self):
        envs=[r.RevisionEnvironment(arm=arm) for arm in r.ARMS]
        initial=[e.reset(seed=2560000,task_id=self.task.task_id).model_dump() for e in envs]
        self.assertEqual(*initial)
        return envs

    def test_only_review_reminder_differs_without_touching_proposal(self):
        envs=self.environments();feedback=[]
        for env in envs:
            value=env.step(DirectRepairAction(content=self.good))
            self.assertFalse(value.done);self.assertEqual(value.reward,0)
            self.assertEqual(env._direct._files[SOURCE_PATH],self.good)
            feedback.append(json.loads(value.feedback))
        self.assertEqual(feedback[1].pop('final_output_domain_reminder'),r.REMINDER)
        self.assertEqual(*feedback)
        self.assertEqual(feedback[0]['diagnostic']['kind'],'computed_result_withheld')

    def test_good_proposal_can_still_regress_no_controller_projection(self):
        native=DirectRepairEnvironment();native.reset(seed=2560000,task_id=self.task.task_id)
        expected=native.step(DirectRepairAction(content=self.extra))
        self.assertLess(expected.reward,1)
        for env in self.environments():
            env.step(DirectRepairAction(content=self.good))
            final=env.step(DirectRepairAction(content=self.extra))
            self.assertEqual(final.reward,expected.reward)
            self.assertEqual(env._direct._files[SOURCE_PATH],self.extra)

    def test_empty_final_retains_actual_first_module_and_terminal_is_idempotent(self):
        for env in self.environments():
            env.step(DirectRepairAction(content=self.good))
            final=env.step(DirectRepairAction(content=''))
            self.assertEqual(final.reward,1);self.assertTrue(final.done)
            self.assertEqual(env.step(DirectRepairAction(content=self.extra)),final)
            self.assertEqual(env._direct._files[SOURCE_PATH],self.good)

    def test_program_unavailability_is_common_and_never_an_answer(self):
        values=[]
        for env in self.environments():
            first=env.step(DirectRepairAction(content='import os'))
            feedback=json.loads(first.feedback);feedback.pop('final_output_domain_reminder',None)
            values.append(feedback)
            self.assertEqual(env.step(DirectRepairAction(content='')).reward,0)
        self.assertEqual(*values)
        self.assertEqual(values[0]['diagnostic']['reason'],'compile_rejected')

    def test_unseen_case_refused_before_native_reset_and_live_factory_closed(self):
        for arm in r.ARMS:
            with patch.object(DirectRepairEnvironment,'reset',side_effect=AssertionError('must not materialize')):
                with self.assertRaises(ValueError):r.RevisionEnvironment(arm=arm).reset(seed=999,task_id=self.task.task_id)
        with self.assertRaises(ValueError):r.materialize()

    def test_plan_preserves_original_resource_scope_and_no_live_permission(self):
        value=r.plan();self.assertEqual(value['limits'],r.original.plan()['limits'])
        self.assertEqual(value['max_requests_per_phase'],16)
        self.assertFalse(value['live_execution_ready']);self.assertFalse(value['comparison_protocol_qualified'])
        self.assertFalse(value['screen_case_selected']);self.assertFalse(value['confirmation_case_selected'])

if __name__=='__main__':unittest.main()
