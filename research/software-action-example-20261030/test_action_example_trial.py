"""Actual Native Trial checks with trusted reference controls, never model results."""
import json
import unittest

import action_example_protocol as protocol


class ActualTrialTests(unittest.TestCase):
    def trials(self):
        jobs = protocol.schedule('screen')
        return [protocol.Trial(next(j for j in jobs if j['arm'] == a))
                for a in protocol.ARMS]

    def test_real_first_messages_differ_only_in_fixed_note(self):
        from action_example_environment import ACTION_EXAMPLE_NOTE
        a, b = self.trials()
        self.assertEqual(a.messages[0], b.messages[0])
        one, two = [json.loads(t.messages[1]['content']) for t in (a, b)]
        self.assertEqual(two.pop('prompt'), one.pop('prompt') + ACTION_EXAMPLE_NOTE)
        self.assertEqual(one, two)
        captures = [protocol.capture(t.job) for t in (a, b)]
        self.assertEqual(captures[0]['problem_sha256'], captures[1]['problem_sha256'])
        self.assertNotEqual(captures[0]['prompt_sha256'], captures[1]['prompt_sha256'])
        self.assertEqual(captures[0]['messages'], a.messages)
        self.assertEqual(captures[1]['messages'], b.messages)

    def test_reference_then_empty_retains_same_final_full_native_grade(self):
        from repair_env.tasks import make_task
        a, b = self.trials()
        reference = make_task(protocol.TASK, protocol.SEEDS['screen']).reference_source
        first = [t.consume(json.dumps({'content': reference, 'submit': True})) for t in (a, b)]
        self.assertEqual(first[0], first[1])
        self.assertEqual(first[0], dict(category='awaiting_revision', done=False,
                                        native_reward=0, semantic_reward=None))
        self.assertEqual(a.native, b.native)
        for t in (a, b):
            review = json.loads(t.native[0]['feedback'])
            self.assertTrue(review['public_only'])
            self.assertFalse(review['hidden_access'])
        final = [t.consume('{"content":""}') for t in (a, b)]
        self.assertEqual(final[0], final[1])
        self.assertEqual(final[0]['category'], 'full')
        self.assertEqual(final[0]['semantic_reward'], 1)
        self.assertTrue(final[0]['done'])
        for t in (a, b):
            self.assertEqual(t.turn, 2)
            self.assertEqual(len(t.messages), 6)
            with self.assertRaises(ValueError): t.consume('{"content":""}')

    def test_initial_wrong_then_reference_is_two_responses_with_public_review(self):
        from repair_env.tasks import make_task
        task = make_task(protocol.TASK, protocol.SEEDS['screen'])
        for t in self.trials():
            first = t.consume(json.dumps({'content': task.initial_source}))
            self.assertEqual(first['category'], 'awaiting_revision')
            self.assertEqual(first['native_reward'], 0)
            final = t.consume(json.dumps({'content': task.reference_source}))
            self.assertEqual(final['category'], 'full')
            self.assertEqual(final['native_reward'], 1)

    def test_schema_echo_still_terminates_without_recovery_or_second_call(self):
        a, b = self.trials()
        echo = json.dumps(a.action_type.model_json_schema())
        results = [t.consume(echo) for t in (a, b)]
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0]['category'], 'wrong')
        for t in (a, b):
            self.assertEqual(t.turn, 1)
            self.assertEqual(len(t.native), 1)
            self.assertTrue(t.closed)
            with self.assertRaises(ValueError): t.consume(echo)

    def test_invalid_json_is_format_failure_without_native_step_or_retry(self):
        for t in self.trials():
            result = t.consume('not an action')
            self.assertEqual(result, dict(category='format', done=True,
                                          native_reward=None, semantic_reward=None))
            self.assertEqual(t.native, [])
            self.assertEqual(len(t.messages), 2)
            with self.assertRaises(ValueError): t.consume('{}')


if __name__ == '__main__': unittest.main()
