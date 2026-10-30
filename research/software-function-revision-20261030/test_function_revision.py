import ast
import json
import unittest
from function_revision import (replace_blocks, source_digest,
    FunctionRevisionEnvironment, FunctionRevisionAction)
from repair_env.tasks import make_task


class FunctionRevisionTests(unittest.TestCase):
    def test_arbitrary_existing_helper_and_new_helper_preserve_others(self):
        before = 'def first(x):\n return x\n\n# retained comment\ndef second(x):\n return x+1\n'
        edits = 'def second(x):\n return third(x)\ndef third(x):\n return x+2\n'
        merged = replace_blocks(before, edits, source_digest(before))
        self.assertTrue(merged.startswith('def first(x):\n return x\n\n# retained comment\n'))
        self.assertEqual([n.name for n in ast.parse(merged).body], ['first', 'second', 'third'])

    def test_stale_hash_duplicate_nonfunction_and_source_limit_rejected(self):
        before = 'def a(x):\n return x\n'
        for code, lease in [('def a(x):\n return 2\n', '0'*64),
                            ('def a(x):\n return 2\ndef a(x):\n return 3\n', source_digest(before)),
                            ('import os', source_digest(before)),
                            ('def a(x):\n return "'+'a'*8200+'"', source_digest(before))]:
            with self.subTest(code=code[:20]), self.assertRaises(ValueError):
                replace_blocks(before, code, lease)

    def test_real_native_final_function_revision_and_module_are_equal(self):
        task_id, seed = 'software_repair-ignore-d3', 3060000
        task = make_task(task_id, seed)
        observations = []
        for arm in ('module_review', 'function_review'):
            env = FunctionRevisionEnvironment(arm=arm)
            initial = env.reset(task_id=task_id, seed=seed)
            observations.append(initial.model_dump())
            first = env.step(FunctionRevisionAction(content=task.initial_source))
            self.assertFalse(first.done)
            self.assertEqual(first.reward, 0)
            feedback = json.loads(first.feedback)
            # All reference definitions are a scripted Native control, never a model solve.
            action = FunctionRevisionAction(mode='functions', content=task.reference_source,
                base_sha256=feedback['revision_base_sha256'])
            final = env.step(action)
            self.assertEqual(final.reward, 1)
            self.assertEqual(env.step(action), final)
        self.assertEqual(observations[0], observations[1])

    def test_invalid_revision_never_grades_retained_good_proposal(self):
        env = FunctionRevisionEnvironment(arm='function_review')
        task = make_task('software_repair-ignore-d3', 3060000)
        env.reset(task_id=task.task_id, seed=task.seed)
        env.step(FunctionRevisionAction(content=task.reference_source))
        final = env.step(FunctionRevisionAction(mode='functions', content=task.reference_source,
                                               base_sha256='0'*64))
        self.assertTrue(final.done)
        self.assertEqual(final.reward, 0)
        self.assertTrue(env._revision_error)


if __name__ == '__main__':
    unittest.main()
