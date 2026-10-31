import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path
from function_revision import (replace_blocks, source_digest,
    FunctionRevisionEnvironment, FunctionRevisionAction)
from repair_env.tasks import make_task


class FunctionRevisionTests(unittest.TestCase):
    def test_cold_protocol_import_keeps_its_own_assessment_module(self):
        root=Path(__file__).resolve().parent
        code=("import sys;from pathlib import Path;root=Path("+repr(str(root))+ ");"
              "sys.path.insert(0,str(root));import caller;p,_=caller.modules();import assemble;"
              "assert Path(p.__file__).resolve()==root/'feedback_protocol.py';"
              "assert Path(assemble.__file__).resolve()==root/'assemble.py'")
        subprocess.run([sys.executable,'-c',code],check=True,timeout=15,
                       stdout=subprocess.PIPE,stderr=subprocess.PIPE)
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

    def test_one_helper_block_repairs_public_runtime_error_without_resending_module(self):
        task = make_task('software_repair-ignore-d3', 3060000)
        tree = ast.parse(task.reference_source)
        entry = next(n for n in tree.body if n.name == task.entrypoint)
        entry.body.insert(0, ast.parse('_unused = _probe([])').body[0])
        tree.body += ast.parse('def _probe(items):\n return range(items)\n').body
        proposed = ast.unparse(ast.fix_missing_locations(tree))
        env = FunctionRevisionEnvironment(arm='function_review')
        env.reset(task_id=task.task_id, seed=task.seed)
        review = env.step(FunctionRevisionAction(content=proposed))
        feedback = json.loads(review.feedback)
        self.assertIn('source_diagnostic', feedback)
        patch = 'def _probe(items):\n return len(items)\n'
        final = env.step(FunctionRevisionAction(mode='functions', content=patch,
            base_sha256=feedback['revision_base_sha256']))
        self.assertEqual(final.reward, 1)
        self.assertTrue(env._applied_function_revision)
        self.assertLess(len(patch), len(proposed))


if __name__ == '__main__':
    unittest.main()
