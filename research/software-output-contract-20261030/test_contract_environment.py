"""Native task/grade parity and absence of feedback-dependent advice."""
import json
import unittest
from contract_environment import ContractEnvironment, CONTRACT_NOTE
from mandatory_environment import ProposalAction
from repair_env.tasks import make_task


class ContractParityTests(unittest.TestCase):
    def test_only_fixed_public_note_differs_at_reset(self):
        for seed in (42, 710, 4022):
            a = ContractEnvironment(arm='standard_contract')
            b = ContractEnvironment(arm='explicit_contract')
            one = a.reset(task_id='software_repair-ignore-d2', seed=seed).model_dump()
            two = b.reset(task_id='software_repair-ignore-d2', seed=seed).model_dump()
            self.assertEqual(two.pop('prompt'), one.pop('prompt') + CONTRACT_NOTE)
            self.assertEqual(one, two)
            self.assertEqual(a._direct._core._task, b._direct._core._task)

    def test_equal_proposals_have_equal_public_feedback_and_native_grades(self):
        task = make_task('software_repair-ignore-d2', 42)
        for source in (task.initial_source, task.reference_source):
            a = ContractEnvironment(arm='standard_contract')
            b = ContractEnvironment(arm='explicit_contract')
            for env in (a, b):
                env.reset(task_id=task.task_id, seed=task.seed)
            one = a.step(ProposalAction(content=source)).model_dump()
            two = b.step(ProposalAction(content=source)).model_dump()
            self.assertEqual(one, two)
            self.assertFalse(one['done'])
            self.assertEqual(one['reward'], 0)
            self.assertFalse(json.loads(one['feedback'])['hidden_access'])
            one = a.step(ProposalAction(content='')).model_dump()
            two = b.step(ProposalAction(content='')).model_dump()
            self.assertEqual(one, two)
            self.assertTrue(one['done'])

    def test_unknown_arm_is_rejected(self):
        with self.assertRaises(ValueError):
            ContractEnvironment(arm='unbound')


if __name__ == '__main__':
    unittest.main()
