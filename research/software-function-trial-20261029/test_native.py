"""Pending ruOS integration tests: actual native environments, not model calls."""
import ast
import json
from pathlib import Path
import sys
import unittest
from trial import Trial

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / p) for p in (
    'research/software-function-block-protocol-20261028',
    'research/software-function-edit-20261028',
    'integrations/software-repair')]
from protocol import capture, schedule
from repair_env.tasks import make_task
from function_edit import TARGETS


def prepared(arm):
    job = next(j for j in schedule('screen', 'native-trial-control') if j['arm'] == arm)
    frozen = capture(job['task_id'], job['seed'], arm)
    return Trial(job, frozen['prompt_sha256'], frozen['problem_sha256']), job, frozen


class NativeTests(unittest.TestCase):
    def test_reference_repair_uses_native_full_grader_in_both_arms(self):
        for arm in ('full_module', 'function_block_available'):
            trial, job, frozen = prepared(arm)
            ref = make_task(job['task_id'], job['seed']).reference_source
            if arm == 'function_block_available':
                node = next(n for n in ast.parse(ref).body if isinstance(n, ast.FunctionDef) and n.name == TARGETS[job['task_id']])
                ref = ''.join(ref.splitlines(keepends=True)[node.lineno-1:node.end_lineno])
            self.assertEqual(trial.messages, frozen['messages'])
            result = trial.consume(json.dumps({'content': ref}), finish_reason='stop')
            self.assertEqual(result['category'], 'full')
            self.assertEqual(result['native_reward'], 1)
            self.assertNotIn('hidden_wrong_answers', json.dumps(trial.messages))
    def test_function_edit_rejection_and_interpreter_failure_stay_distinct(self):
        trial, _, _ = prepared('function_block_available')
        r = trial.consume(json.dumps({'content': 'import os'}), finish_reason='stop')
        self.assertEqual(r['category'], 'edit_rejection')
        trial, _, _ = prepared('full_module')
        r = trial.consume(json.dumps({'content': 'import os'}), finish_reason='stop')
        self.assertEqual(r['category'], 'execution')
        self.assertIsNone(r['semantic_reward'])
    def test_full_module_fallback_remains_available_in_treatment(self):
        trial, job, _ = prepared('function_block_available')
        ref = make_task(job['task_id'], job['seed']).reference_source
        r = trial.consume(json.dumps({'mode': 'module', 'content': ref}), finish_reason='stop')
        self.assertEqual(r['category'], 'full')
        with self.assertRaises(ValueError): trial.consume('{}', finish_reason='stop')


if __name__ == '__main__': unittest.main()
