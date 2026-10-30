import json
import unittest
from types import SimpleNamespace
from repair_env.runner import Program, Rejected
from public_runtime_diagnostics import TracedProgram, diagnose_public


class PublicTask:
    entrypoint = 'solve'
    public = [SimpleNamespace(args=([1, 2],))]

    @property
    def hidden(self):
        raise AssertionError('diagnostics must never access hidden cases')


class RuntimeDiagnosticTests(unittest.TestCase):
    def test_public_range_type_error_location_without_values(self):
        source = 'def solve(items):\n return list(range(items))\n'
        value = diagnose_public(source, PublicTask())
        self.assertEqual(value['diagnostics'], [dict(public_example=1,
            error_type='TypeError', line=2, byte_column=13, node='Call', call='range')])
        self.assertEqual(set(value), {'kind', 'scope', 'diagnostics'})
        self.assertNotIn('[1, 2]', json.dumps(value))

    def test_native_output_and_steps_preserved(self):
        source = 'def solve(items):\n return list(range(len(items)))\n'
        a, b = Program(source), TracedProgram(source)
        self.assertEqual(a.run('solve', ([1, 2],)), b.run('solve', ([1, 2],)))
        self.assertEqual(a.steps, b.steps)
        self.assertIsNone(diagnose_public(source, PublicTask()))

    def test_native_error_and_steps_preserved(self):
        source = 'def solve(items):\n return list(range(items))\n'
        a, b = Program(source), TracedProgram(source)
        for p in (a, b):
            with self.assertRaises(TypeError):
                p.run('solve', ([1, 2],))
        self.assertEqual(a.steps, b.steps)

    def test_step_guard_is_unchanged(self):
        source = 'def solve(items):\n while True:\n  pass\n'
        a, b = Program(source), TracedProgram(source)
        for p in (a, b):
            with self.assertRaises(Rejected):
                p.run('solve', ([],))
        self.assertEqual(a.steps, b.steps)

    def test_no_diagnostic_on_compile_rejection(self):
        self.assertIsNone(diagnose_public('import os', PublicTask()))

    def test_public_case_limit(self):
        task = PublicTask()
        task.public = task.public * 50
        value = diagnose_public('def solve(items):\n return range(items)\n', task)
        self.assertEqual(len(value['diagnostics']), 8)

    def test_state_is_reset_between_runs(self):
        p = TracedProgram('def solve(items):\n return range(items)\n')
        with self.assertRaises(TypeError):
            p.run('solve', ([],))
        self.assertIsNotNone(p.source_location)
        self.assertEqual(p.run('solve', (2,)), [0, 1])
        self.assertIsNone(p.source_location)


if __name__ == '__main__':
    unittest.main()
