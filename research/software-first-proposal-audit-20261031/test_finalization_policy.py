"""Existing-case trusted Native controls; no model or provider calls."""
import json
from pathlib import Path
import sys
import unittest

from finalization_policy import FinalizationPolicy, observation_tokens

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'research/software-action-example-20261030'),
                str(ROOT/'integrations/software-repair')]
import action_example_protocol as protocol
from repair_env.tasks import make_task


class PolicyTests(unittest.TestCase):
    def trial(self, arm):
        # Previously materialized qualification case; never instantiate planned
        # screen 3120000 or reserved confirmation 3130000 in these controls.
        job = protocol.schedule('screen')[0]
        return FinalizationPolicy(protocol.Trial(job), arm=arm), make_task(job['task_id'], job['seed'])

    def test_identical_initial_prompt_and_controller_grade_at_original_native_reward(self):
        baseline, task = self.trial('standard_revision')
        treatment, _ = self.trial('public_pass_finalize')
        self.assertEqual(baseline.request_messages, treatment.request_messages)
        reply = json.dumps(dict(content=task.reference_source))
        b = baseline.consume_model(reply, finish_reason='stop')
        t = treatment.consume_model(reply, finish_reason='stop')
        self.assertFalse(b['done']); self.assertEqual(b['native_reward'], 0)
        self.assertTrue(t['done']); self.assertEqual(t['native_reward'], 1)
        self.assertEqual(t['model_responses'], 1)
        self.assertEqual(len(t['controller_actions']), 1)
        self.assertEqual(len(t['new_observations']), 2)
        self.assertEqual(len(b['new_observations']), 1)
        self.assertEqual(observation_tokens(t, lambda _: 17), 34)
        self.assertEqual(observation_tokens(b, lambda _: 17), 17)
        with self.assertRaises(ValueError): _ = treatment.request_messages
        with self.assertRaises(ValueError): treatment.consume_model(reply, finish_reason='stop')

    def test_public_failure_preserves_second_model_response(self):
        treatment, task = self.trial('public_pass_finalize')
        first = treatment.consume_model(json.dumps(dict(content=task.initial_source)), finish_reason='stop')
        self.assertFalse(first['done']); self.assertEqual(first['controller_actions'], [])
        final = treatment.consume_model(json.dumps(dict(content=task.reference_source)), finish_reason='stop')
        self.assertEqual(final['category'], 'full')
        self.assertEqual(final['model_responses'], 2)
        self.assertEqual(final['controller_actions'], [])

    def test_truncation_is_not_silently_finalized(self):
        treatment, _ = self.trial('public_pass_finalize')
        for reason in ['length', 'error', None]:
            with self.assertRaises(ValueError): treatment.consume_model('{', finish_reason=reason)
        self.assertEqual(treatment.model_responses, 0)
        self.assertEqual(treatment.trial.native, [])

    def test_malformed_action_keeps_original_format_failure(self):
        treatment, _ = self.trial('public_pass_finalize')
        result = treatment.consume_model('{', finish_reason='stop')
        self.assertEqual(result['category'], 'format')
        self.assertTrue(result['done'])
        self.assertEqual(result['controller_actions'], [])


if __name__ == '__main__': unittest.main()
