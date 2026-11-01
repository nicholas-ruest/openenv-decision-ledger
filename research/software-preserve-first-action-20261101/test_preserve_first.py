"""Actual Native controls on one already-seen case, not model evaluation."""
import argparse
import copy
import json
import os
import sys
from pathlib import Path
import unittest

import preserve_first as p


class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p.QualificationBinding(p.qualification_job('baseline'))

    def trials(self):
        return [p.QualificationTrial(p.qualification_job(a)) for a in p.ARMS]

    def test_only_initial_prompt_changes_with_identical_native_schema_and_problem(self):
        a, b = self.trials()
        self.assertEqual(a.messages[0], b.messages[0])
        one, two = [json.loads(t.messages[1]['content']) for t in (a, b)]
        self.assertEqual(two.pop('prompt'), one.pop('prompt') + p.policy.guidance(p.TASK))
        self.assertEqual(one, two)
        self.assertEqual(a.binding.problem_sha256, b.binding.problem_sha256)
        self.assertNotEqual(a.binding.prompt_sha256, b.binding.prompt_sha256)

    def test_original_full_module_action_is_not_changed_and_has_same_terminal_grade(self):
        from repair_env.tasks import make_task, SOURCE_PATH
        reference = make_task(p.TASK, p.QUALIFICATION_SEED).reference_source
        reply = json.dumps({'content': reference})
        for trial in self.trials():
            result = trial.consume(reply, finish_reason='stop')
            self.assertEqual(result['category'], 'full')
            self.assertEqual(result['native_reward'], 1)
            self.assertEqual(result['semantic_reward'], 1)
            self.assertEqual(result['controller_actions'], [])
            self.assertEqual(trial.binding.env._files[SOURCE_PATH], reference)
            self.assertEqual(trial.messages[2]['content'], reply)
            self.assertEqual(result['new_observations'], [trial.native])
            self.assertEqual(len(trial.messages), 4)
            self.assertNotIn('hidden_wrong_answers', trial.messages[-1]['content'])
            with self.assertRaises(ValueError): trial.consume(reply, finish_reason='stop')

    def test_unchanged_source_and_execution_failure_remain_separate(self):
        a, b = self.trials()
        source = json.loads(a.messages[1]['content'])['source']
        wrong = a.consume(json.dumps({'content': source}), finish_reason='stop')
        self.assertEqual(wrong['category'], 'wrong')
        failed = b.consume('{"content":"import os"}', finish_reason='stop')
        self.assertEqual(failed['category'], 'execution')
        self.assertIsNone(failed['semantic_reward'])

    def test_truncated_provider_and_format_responses_close_without_native_action(self):
        for reason, text, category in [('length', '{}', 'truncation'),
                                       ('error', '{}', 'provider'),
                                       ('stop', 'invalid json', 'format')]:
            for trial in self.trials():
                result = trial.consume(text, finish_reason=reason)
                self.assertEqual(result['category'], category)
                self.assertEqual(result['new_observations'], [])
                self.assertIsNone(trial.native)
                with self.assertRaises(ValueError): trial.consume('{}', finish_reason='stop')

    def test_new_cases_and_live_materialization_fail_before_native_reset(self):
        original = p.qualification_job('baseline')
        for field, value in [('seed', 3180000), ('phase', 'screen'),
                             ('task_id', 'software_repair-ignore-d4'), ('extra', True)]:
            job = copy.deepcopy(original); job[field] = value
            with self.assertRaises(ValueError): p.QualificationTrial(job)
        with self.assertRaises(ValueError): p.materialize(original)

    def test_actual_terminal_observation_is_charged_with_pinned_tokenizer(self):
        from repair_env.tasks import make_task
        sys.path.insert(0, str(p.ROOT / 'integrations/openenv-arena'))
        calibrate = p.load('preserve_first_counter', 'integrations/openenv-arena/scripts/calibrate.py')
        counter = calibrate.load_counter(argparse.Namespace(accounting='arena',
            tokenizer_json=Path(os.environ['HELPER_TEST_TOKENIZER']),
            tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
        reply = json.dumps({'content': make_task(p.TASK, p.QUALIFICATION_SEED).reference_source})
        for trial in self.trials():
            result = trial.consume(reply, finish_reason='stop')
            observed = sum(counter.count(p.canonical(x)) for x in result['new_observations'])
            self.assertGreater(observed, 0)
            self.assertLessEqual(observed, p.limits()['final_observation_reserve'])
            self.assertLessEqual(counter.count(reply) + observed, 8192)
            self.assertLessEqual(counter.context(trial.messages), 24576)


if __name__ == '__main__': unittest.main()
