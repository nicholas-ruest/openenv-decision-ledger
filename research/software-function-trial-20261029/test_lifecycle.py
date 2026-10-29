"""Fictional binding tests only; not native OpenEnv/environment validation."""
import copy
import json
import unittest
from trial import Trial


class FictionalBinding:
    def __init__(self, job):
        self.prompt_sha256 = 'a' * 64
        self.problem_sha256 = 'b' * 64
        self.messages = [{'role': 'user', 'content': 'fictional public prompt'}]
        self.steps = 0
    def parse(self, reply):
        return json.loads(reply)
    def step(self, action):
        self.steps += 1
        return dict(done=True, reward=.5, error='')
    def diagnose(self, native):
        return dict(category='partial', native_reward=.5, semantic_reward=.5,
                    diagnostic_only='fictional hidden aggregate')


class LifecycleTests(unittest.TestCase):
    def trial(self, factory=FictionalBinding):
        return Trial({'arm': 'fictional-test-only'}, 'a'*64, 'b'*64, binding_factory=factory)
    def test_single_consumption_and_diagnostics_excluded_from_transcript(self):
        t = self.trial(); original = copy.deepcopy(t.messages)
        r = t.consume('{"content":"fictional"}', finish_reason='stop')
        self.assertEqual(r['semantic_reward'], .5)
        self.assertEqual(t.binding.steps, 1)
        self.assertNotIn('diagnostic_only', json.dumps(t.messages))
        self.assertEqual(t.messages[:1], original)
        with self.assertRaises(ValueError): t.consume('{}', finish_reason='stop')
    def test_invalid_and_truncated_responses_never_step_or_retry(self):
        for text, finish, expected in [('bad json','stop','format'),('{}','length','truncation'),('{}',None,'provider'),(None,'stop','format')]:
            t = self.trial(); r = t.consume(text, finish_reason=finish)
            self.assertEqual(r['category'], expected); self.assertEqual(t.binding.steps, 0)
            with self.assertRaises(ValueError): t.consume('{}', finish_reason='stop')
    def test_external_abort_is_terminal_without_native_grade(self):
        t = self.trial(); r = t.abort('budget')
        self.assertIsNone(r['native_reward']); self.assertEqual(t.binding.steps, 0)
        with self.assertRaises(ValueError): t.consume('{}', finish_reason='stop')
    def test_frozen_input_mismatch_refuses_trial(self):
        with self.assertRaises(ValueError):
            Trial({}, 'c'*64, 'b'*64, binding_factory=FictionalBinding)
    def test_native_contract_failure_closes_before_any_retry(self):
        class Nonterminal(FictionalBinding):
            def step(self, action): return dict(done=False, reward=0, error='')
        t = self.trial(Nonterminal)
        with self.assertRaises(ValueError): t.consume('{}', finish_reason='stop')
        with self.assertRaises(ValueError): t.consume('{}', finish_reason='stop')


if __name__ == '__main__': unittest.main()
