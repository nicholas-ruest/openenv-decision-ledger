"""Existing-case scripted Native controls, never model performance evidence."""
import json
from pathlib import Path
import sys
import unittest

from helper_policy import HelperPreservationPolicy, preserve_helpers, DECLARATION, observation_tokens

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'research/software-action-example-20261030'),
               str(ROOT/'integrations/software-repair')]
from action_example_protocol import Trial, schedule
from repair_env.tasks import make_task


class HelperPolicyTests(unittest.TestCase):
    def trial(self, arm):
        # Existing qualification case only; no future screen/confirmation case.
        job = schedule('screen')[0]
        self.assertEqual(job['seed'], 3100000)
        return HelperPreservationPolicy(Trial(job), arm=arm), make_task(job['task_id'], job['seed'])

    def test_native_repair_of_corrupted_declared_helper_is_controller_authored(self):
        baseline, task = self.trial('standard_revision')
        candidate, _ = self.trial('preserve_declared_helpers')
        self.assertEqual(baseline.trial.messages, candidate.trial.messages)
        source = task.reference_source.replace('return table[len(tokens)][len(word)]', 'return False')
        self.assertNotEqual(source, task.reference_source)
        actual_reply = json.dumps(dict(content=source))
        first = candidate.consume_model(actual_reply, finish_reason='stop')
        self.assertFalse(first['done'])  # helper preservation never auto-finalizes
        self.assertEqual(len(first['new_observations']), 1)
        self.assertEqual(first['controller_actions'][0]['restored_names'], ['match_segment'])
        self.assertEqual(first['controller_actions'][0]['authored_by'], 'controller')
        self.assertEqual(candidate.trial.messages[2], dict(role='assistant', content=actual_reply))
        self.assertEqual(len(first['controller_observations']), 1)
        self.assertIn('controller_observation', json.loads(candidate.trial.messages[-1]['content']))
        self.assertEqual(observation_tokens(first, lambda text: 1), 2)
        baseline.consume_model(json.dumps(dict(content=source)), finish_reason='stop')
        final = candidate.consume_model(json.dumps(dict(content='')), finish_reason='stop')
        old = baseline.consume_model(json.dumps(dict(content='')), finish_reason='stop')
        self.assertEqual(final['category'], 'full')
        self.assertNotEqual(old['category'], 'full')
        self.assertEqual(len(final['new_observations']), 1)
        self.assertEqual(final['controller_observations'], [])
        self.assertEqual(len(final['controller_actions']), 1)

    def test_unrepaired_targets_are_never_replaced_by_a_reference_solution(self):
        candidate, _ = self.trial('preserve_declared_helpers')
        original = candidate.source
        value = preserve_helpers(original, original, candidate.prompt)
        self.assertFalse(value['changed'])
        self.assertEqual(value['content'], original)
        candidate.consume_model(json.dumps(dict(content=original)), finish_reason='stop')
        final = candidate.consume_model(json.dumps(dict(content='')), finish_reason='stop')
        self.assertNotEqual(final['category'], 'full')
        self.assertEqual(final['controller_actions'], [])

    def test_missing_declaration_malformed_and_duplicate_definitions_are_untouched(self):
        c, _ = self.trial('preserve_declared_helpers')
        for content, prompt in [('def broken(', c.prompt),
                                (c.source, c.prompt.replace(DECLARATION, '')),
                                (c.source+'\ndef match_parts(x,y):\n    return False\n', c.prompt)]:
            with self.subTest(content=content[:25]):
                value = preserve_helpers(c.source, content, prompt)
                self.assertFalse(value['changed'])
                self.assertEqual(value['content'], content)
        with self.assertRaises(ValueError):
            c.consume_model('{"content":"unfinished', finish_reason='length')
        self.assertEqual(c.model_responses, 0)


if __name__ == '__main__':
    unittest.main()
