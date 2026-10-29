"""Standard Python loop-else semantics, without executing submitted code on host."""
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('loop_else_runner',(Path(__file__).with_name('runner.py') if Path(__file__).with_name('runner.py').exists() else ROOT/'integrations/software-repair/repair_env/runner.py'))
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)

class LoopElseTests(unittest.TestCase):
    def run_program(self,body,args=()):
        return runner.Program('def f(values):\n'+''.join('    '+s+'\n' for s in body.splitlines())).run('f',[list(args)])
    def test_for_empty_exhaustion_continue_and_break(self):
        body='out = []\nfor x in values:\n    if x == 1:\n        continue\n    if x < 0:\n        break\n    out.append(x)\nelse:\n    out.append(99)\nreturn out'
        self.assertEqual(self.run_program(body),[99])
        self.assertEqual(self.run_program(body,[1,2]),[2,99])
        self.assertEqual(self.run_program(body,[2,-1,3]),[2])
    def test_while_zero_exhaustion_and_break(self):
        body='i = 0\nwhile i < len(values):\n    if values[i] < 0:\n        break\n    i += 1\nelse:\n    return 99\nreturn i'
        self.assertEqual(self.run_program(body),99)
        self.assertEqual(self.run_program(body,[1,2]),99)
        self.assertEqual(self.run_program(body,[2,-1]),1)
    def test_nested_break_only_suppresses_own_loop_else(self):
        body='out = []\nfor x in values:\n    for y in [0]:\n        break\n    else:\n        out.append(-1)\n    out.append(x)\nelse:\n    out.append(99)\nreturn out'
        self.assertEqual(self.run_program(body,[3,4]),[3,4,99])
    def test_break_in_inner_else_targets_outer_loop(self):
        body='out = []\nfor x in values:\n    for y in []:\n        pass\n    else:\n        break\n    out.append(x)\nelse:\n    out.append(99)\nreturn out'
        self.assertEqual(self.run_program(body,[3]),[])
        self.assertEqual(self.run_program(body,[]),[99])
    def test_control_in_else_without_enclosing_loop_rejected(self):
        for control in ['break','continue']:
            for loop in ['for x in values:','while False:']:
                with self.assertRaises(runner.Rejected):
                    runner.Program('def f(values):\n    '+loop+'\n        pass\n    else:\n        '+control+'\n    return 0\n')
    def test_else_remains_inside_existing_step_budget(self):
        with self.assertRaises(runner.Rejected):
            self.run_program('for x in []:\n    pass\nelse:\n    while True:\n        pass\nreturn 0')

if __name__=='__main__':unittest.main()
