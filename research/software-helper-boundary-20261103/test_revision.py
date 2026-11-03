import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('boundary_candidate', Path(__file__).with_name('revision_environment.py'))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
from repair_env.direct_environment import DirectRepairAction, DirectRepairEnvironment
from repair_env.tasks import SOURCE_PATH

# Small independently authored wrong module; no private response is copied.
WRONG = 'def classify_ignore(ignore_lines, entries):\n    return {}\n'


class BoundaryTests(unittest.TestCase):
    def environments(self):
        envs = [r.RevisionEnvironment(arm=arm) for arm in r.ARMS]
        initial = [env.reset(seed=2560000, task_id='software_repair-ignore-d3').model_dump() for env in envs]
        self.assertEqual(*initial)
        self.assertNotIn(r.REMINDER, json.dumps(initial))
        return envs

    def test_review_differs_only_by_reminder_and_empty_final_keeps_actual_wrong_code(self):
        envs = self.environments()
        observations = []
        for env in envs:
            first = env.step(DirectRepairAction(content=WRONG))
            self.assertFalse(first.done)
            self.assertEqual(first.reward, 0)
            self.assertEqual(env._direct._files[SOURCE_PATH], WRONG)
            observations.append(first.model_dump())
        feedback = [json.loads(o['feedback']) for o in observations]
        self.assertEqual(feedback[1].pop('helper_input_boundary_reminder'), r.REMINDER)
        self.assertEqual(*feedback)
        self.assertEqual(feedback[0]['diagnostic']['kind'], 'computed_result_withheld')
        observations[1]['feedback'] = observations[0]['feedback']
        self.assertEqual(*observations)
        native = DirectRepairEnvironment()
        native.reset(seed=2560000, task_id='software_repair-ignore-d3')
        expected = native.step(DirectRepairAction(content=WRONG))
        self.assertLess(expected.reward, 1)
        for env in envs:
            terminal = env.step(DirectRepairAction(content=''))
            self.assertTrue(terminal.done)
            self.assertEqual(terminal.reward, expected.reward)
            self.assertEqual(env._direct._files[SOURCE_PATH], WRONG)
            self.assertEqual(env.step(DirectRepairAction(content='import os')), terminal)

    def test_reminder_does_not_repair_or_rescue_an_invalid_final_module(self):
        for env in self.environments():
            env.step(DirectRepairAction(content=WRONG))
            terminal = env.step(DirectRepairAction(content='import os'))
            self.assertTrue(terminal.done)
            self.assertEqual(terminal.reward, 0)
            self.assertEqual(env._direct._files[SOURCE_PATH], 'import os')

    def test_unseen_case_refused_before_native_reset_and_no_live_factory(self):
        with patch.object(DirectRepairEnvironment, 'reset', side_effect=AssertionError('unseen reset')):
            for arm in r.ARMS:
                with self.assertRaises(ValueError):
                    r.RevisionEnvironment(arm=arm).reset(seed=999, task_id='software_repair-ignore-d3')
        with self.assertRaises(ValueError):
            r.materialize()


if __name__ == '__main__':
    unittest.main()
