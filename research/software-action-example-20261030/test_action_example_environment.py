"""Actual Native parity tests; no provider calls or performance estimates."""
import json
import unittest

from action_example_environment import (
    ACTION_EXAMPLE_NOTE, ActionExampleEnvironment, ProposalAction,
)
from contract_environment import ContractEnvironment, CONTRACT_NOTE
from repair_env.tasks import make_task
from repair_env.environment import RepairAction

TASK = 'software_repair-ignore-d2'


class ActionExampleTests(unittest.TestCase):
    def environments(self, seed=42):
        envs = [ActionExampleEnvironment(arm=a)
                for a in ('schema_only', 'action_example')]
        return envs, [e.reset(task_id=TASK, seed=seed) for e in envs]

    def test_only_reset_prompt_note_differs_and_baseline_is_exact(self):
        for seed in (42, 710, 4022):
            envs, obs = self.environments(seed)
            baseline = ContractEnvironment(arm='standard_contract')
            self.assertEqual(obs[0].model_dump(),
                             baseline.reset(task_id=TASK, seed=seed).model_dump())
            a, b = [o.model_dump() for o in obs]
            self.assertEqual(b.pop('prompt'), a.pop('prompt') + ACTION_EXAMPLE_NOTE)
            self.assertEqual(a, b)
            self.assertNotIn(CONTRACT_NOTE, obs[1].prompt)
            self.assertEqual(envs[0]._direct._core._task, envs[1]._direct._core._task)

    def test_example_has_only_content_and_carries_no_repair_source(self):
        example = ACTION_EXAMPLE_NOTE.split('example: ', 1)[1].split('. Replace', 1)[0]
        self.assertEqual(json.loads(example), {'content': '<complete repaired Python module>'})
        self.assertNotIn('def ', ACTION_EXAMPLE_NOTE)
        self.assertNotIn('submit', ProposalAction.model_json_schema()['properties'])

    def test_same_reference_proposal_review_and_final_grade(self):
        envs, _ = self.environments()
        source = make_task(TASK, 42).reference_source
        reviews = [e.step(ProposalAction(content=source)).model_dump() for e in envs]
        self.assertEqual(reviews[0], reviews[1])
        self.assertFalse(reviews[0]['done'])
        self.assertEqual(reviews[0]['reward'], 0)
        feedback = json.loads(reviews[0]['feedback'])
        self.assertTrue(feedback['public_only'])
        self.assertFalse(feedback['hidden_access'])
        self.assertNotIn(ACTION_EXAMPLE_NOTE, reviews[0]['feedback'])
        finals = [e.step(ProposalAction(content='')).model_dump() for e in envs]
        self.assertEqual(finals[0], finals[1])
        self.assertTrue(finals[0]['done'])
        self.assertEqual(finals[0]['reward'], 1)

    def test_wrong_source_keeps_identical_native_grade(self):
        envs, _ = self.environments()
        source = make_task(TASK, 42).initial_source
        for e in envs:
            e.step(ProposalAction(content=source))
        finals = [e.step(ProposalAction(content='')).model_dump() for e in envs]
        self.assertEqual(finals[0], finals[1])
        self.assertLess(finals[0]['reward'], 1)

    def test_schema_echo_is_not_recovered_retried_or_promoted(self):
        envs, _ = self.environments()
        action = ProposalAction.model_validate_json(json.dumps(ProposalAction.model_json_schema()), strict=True)
        self.assertEqual(action.content, '')
        expected = envs[0]._direct._core.step(RepairAction(op='submit')).reward
        envs, _ = self.environments()
        finals = [e.step(action).model_dump() for e in envs]
        self.assertEqual(finals[0], finals[1])
        self.assertTrue(finals[0]['done'])
        self.assertEqual(finals[0]['reward'], expected)
        self.assertEqual(finals[0]['remaining_responses'], 0)

    def test_first_nonempty_proposal_cannot_submit_hidden_grader(self):
        envs, _ = self.environments()
        for e in envs:
            operations = []
            core = e._direct._core
            original = core.step
            def tracked(action, *args, **kwargs):
                operations.append(action.op)
                return original(action, *args, **kwargs)
            core.step = tracked
            obs = e.step(ProposalAction.model_validate({'content': make_task(TASK, 42).reference_source,
                                                       'submit': True}))
            self.assertEqual(operations, ['write'])
            self.assertFalse(obs.done)
            self.assertEqual(obs.reward, 0)

    def test_wrong_task_or_unbound_arm_is_rejected(self):
        with self.assertRaises(ValueError):
            ActionExampleEnvironment(arm='unbound')
        for arm in ('schema_only', 'action_example'):
            e = ActionExampleEnvironment(arm=arm)
            with self.assertRaises(ValueError):
                e.reset(task_id='software_repair-ignore-d3', seed=42)


if __name__ == '__main__':
    unittest.main()
