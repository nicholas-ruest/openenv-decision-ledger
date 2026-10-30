"""Static trusted CPython fixtures; never execute model responses on the host."""
import copy
import importlib.util
from pathlib import Path
import unittest

target = Path(__file__).with_name('runner.py')
if not target.exists():
    target = Path(__file__).resolve().parents[2] / 'integrations/software-repair/repair_env/runner.py'
spec = importlib.util.spec_from_file_location('sort_key_candidate', target)
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)
Program, Rejected = candidate.Program, candidate.Rejected


class SortKeyCompatibilityTests(unittest.TestCase):
    def compare(self, source, value):
        reference = {}
        # All callers below supply literal, trusted test programs from this file.
        exec(source, reference)
        expected = reference['solve'](copy.deepcopy(value))
        self.assertEqual(Program(source).run('solve', [value]), expected)

    def test_lambda_closure_stability_and_reverse(self):
        for reverse in ('False', 'True', '1', '0'):
            source = ('def solve(xs):\n factor = -1\n out = list(xs)\n'
                      ' out.sort(key=lambda x: factor * x[0], reverse=' + reverse + ')\n return out\n')
            self.compare(source, [[2, 'a'], [1, 'b'], [2, 'c'], [1, 'd']])

    def test_named_and_existing_builtin_keys(self):
        sources = [
            'def priority(x):\n return (-len(x), x)\ndef solve(xs):\n out = list(xs)\n out.sort(key=priority)\n return out\n',
            'def solve(xs):\n out = list(xs)\n out.sort(key=len)\n return out\n',
            'def solve(xs):\n out = list(xs)\n out.sort(key=abs, reverse=True)\n return out\n',
        ]
        for source, value in zip(sources, [['bb', 'a', 'ab', 'ccc'], ['bb', 'a', 'cc', 'd'], [-3, 1, 3, -1]]):
            self.compare(source, value)

    def test_key_called_once_per_item_in_input_order(self):
        source = ('def solve(xs):\n trace = []\n out = list(xs)\n'
                  ' out.sort(key=lambda x: (trace.append(x), x[0])[1])\n return [out, trace]\n')
        self.compare(source, [[2, 'a'], [1, 'b'], [2, 'c']])

    def test_none_key_and_in_place_return_value(self):
        self.compare('def solve(xs):\n out = list(xs)\n value = out.sort(key=None, reverse=False)\n return [out, value]\n', [3, 1, 2])

    def test_unrelated_keywords_and_lambda_contexts_stay_rejected(self):
        for source in [
            'def solve(xs):\n return sorted(xs, key=abs)\n',
            'def solve(xs):\n return lambda x: x\n',
            'def solve(xs):\n xs.sort(unrecognized=True)\n return xs\n',
            'def solve(xs):\n xs.sort(**{})\n return xs\n',
            'def solve(xs):\n xs.sort(key=None, key=abs)\n return xs\n',
            'def solve(xs):\n xs.sort(key=lambda x,y: x)\n return xs\n',
            'def solve(xs):\n xs.sort(reverse=lambda x: x)\n return xs\n',
        ]:
            with self.subTest(source=source), self.assertRaises(Rejected):
                Program(source)

    def test_callback_uses_existing_step_limit(self):
        source = ('def priority(x):\n while True:\n  pass\n'
                  'def solve(xs):\n out = list(xs)\n out.sort(key=priority)\n return out\n')
        with self.assertRaisesRegex(Rejected, 'step limit'):
            Program(source).run('solve', [[2, 1]])

    def test_input_mutation_guard_remains(self):
        value = [2, 1]
        with self.assertRaisesRegex(Rejected, 'input mutation'):
            Program('def solve(xs):\n xs.sort(key=lambda x: x)\n return xs\n').run('solve', [value])
        self.assertEqual(value, [2, 1])

    def test_callback_error_is_not_hidden(self):
        source = 'def solve(xs):\n out = list(xs)\n out.sort(key=lambda x: x[99])\n return out\n'
        with self.assertRaises(IndexError):
            Program(source).run('solve', [[[1], [2]]])


if __name__ == '__main__':
    unittest.main()
