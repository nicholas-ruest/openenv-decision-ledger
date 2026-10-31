"""Trusted Native controls; no model responses, billing or provider access."""
import json
from pathlib import Path
import sys
import unittest

from audit import public_pass, counterfactual

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'research/software-action-example-20261030'),
                str(ROOT / 'integrations/software-repair')]
import action_example_protocol as protocol


class AuditTests(unittest.TestCase):
    def test_trigger_requires_explicit_public_only_complete_counts(self):
        valid = dict(kind='public_field_check', public_only=True, hidden_access=False,
                     passed=6, total=6)
        self.assertTrue(public_pass(valid))
        for change in [dict(passed=5), dict(total=0, passed=0), dict(passed=True),
                       dict(total='6'), dict(hidden_access=True), dict(public_only=1),
                       dict(kind='hidden_grade')]:
            self.assertFalse(public_pass(dict(valid, **change)), change)

    def test_reference_first_proposal_is_retained_by_original_empty_action(self):
        from repair_env.tasks import make_task
        job = protocol.schedule('screen')[0]
        task = make_task(job['task_id'], job['seed'])
        trial = protocol.Trial(job)
        reply = dict(choices=[dict(finish_reason='stop', message=dict(
            content=json.dumps(dict(content=task.reference_source))))])
        value = counterfactual(trial, reply)
        self.assertTrue(value['eligible'])
        self.assertTrue(value['controller_authored_action'])
        self.assertEqual(value['retained_category'], 'full')
        self.assertEqual(value['retained_reward'], 1)
        self.assertEqual(trial.turn, 2)

    def test_public_failure_does_not_invoke_hidden_finalization(self):
        trial = protocol.Trial(protocol.schedule('screen')[0])
        reply = dict(choices=[dict(finish_reason='stop', message=dict(
            content=json.dumps(dict(content=trial.env._direct._core._task.initial_source))))])
        value = counterfactual(trial, reply)
        self.assertFalse(value['eligible'])
        self.assertEqual(trial.turn, 1)
        self.assertFalse(trial.closed)

    def test_truncated_first_response_is_not_recovered(self):
        trial = protocol.Trial(protocol.schedule('screen')[0])
        value = counterfactual(trial, dict(choices=[dict(finish_reason='length',
                    message=dict(content='{"content":'))]))
        self.assertFalse(value['eligible'])
        self.assertEqual(trial.turn, 0)


if __name__ == '__main__':
    unittest.main()
