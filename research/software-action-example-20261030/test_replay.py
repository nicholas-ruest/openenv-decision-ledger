"""Scripted reference traces replay through the actual Native environment.

All responses here are trusted controls, not provider or model evidence.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
import unittest
import action_example_protocol as protocol
from replay import verify_chunk

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'integrations/openenv-arena'))
PIN = '0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'


class ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tokenizer = os.environ.get('ACTION_EXAMPLE_TEST_TOKENIZER')
        if not tokenizer:
            raise unittest.SkipTest('explicit public pinned tokenizer needed for Native replay controls')
        spec = importlib.util.spec_from_file_location(
            'actual_replay_accounting', ROOT / 'integrations/openenv-arena/scripts/calibrate.py')
        helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
        cls.counter = helper.load_counter(argparse.Namespace(
            accounting='arena', tokenizer_json=Path(tokenizer), tokenizer_sha256=PIN))
        cls.bundle = protocol.bundle(0)
        cls.rows, cls.events = cls.reference_traces()

    @classmethod
    def reference_traces(cls):
        from repair_env.tasks import make_task
        rows, events = [], []
        for job in cls.bundle['screen_jobs']:
            trial = protocol.Trial(job); bound = protocol.capture(job)
            task = make_task(job['task_id'], job['seed'])
            generation = observations = context = 0
            calls, identities = [], []
            for turn, source in enumerate((task.initial_source, task.reference_source)):
                limit = min(6000 if turn == 0 else 8096, 8192-generation-observations-96)
                request = dict(protocol.sampling_for(job, turn), messages=copy.deepcopy(trial.messages), max_tokens=limit)
                label = job['attempt_id'] + ':' + str(turn)
                events.append(dict(event='intent', attempt_id=job['attempt_id'], turn=turn,
                    max_tokens=limit, request_sha256=protocol.digest(request),
                    messages_sha256=protocol.digest(trial.messages)))
                events.append(dict(event='reserved', attempt_id=job['attempt_id'], label=label, turn=turn))
                events.append(dict(event='calling', attempt_id=job['attempt_id'], call_id=label, turn=turn))
                content = json.dumps(dict(content=source))
                response = dict(id='scripted-control-' + label,
                    usage=dict(prompt_tokens=cls.counter.context(trial.messages),
                               completion_tokens=cls.counter.count(content)),
                    choices=[dict(message=dict(role='assistant', content=content), finish_reason='stop')])
                events.append(dict(event='response', attempt_id=job['attempt_id'], turn=turn, response=response))
                calls.append(label); identities.append(hashlib.sha256(response['id'].encode()).hexdigest())
                usage = response['usage']; generation += usage['completion_tokens']
                value = trial.consume(content)
                obs = cls.counter.count(protocol.canonical(trial.native[-1]))
                observations += obs
                context = max(context, cls.counter.context(trial.messages),
                              usage['prompt_tokens'] + usage['completion_tokens'] + obs)
            rows.append(dict(job, prompt_sha256=bound['prompt_sha256'], problem_sha256=bound['problem_sha256'],
                call_ids=calls, reservation_labels=calls.copy(), response_ids=identities,
                call_id=calls[0], reservation_label=calls[0],
                response_id=hashlib.sha256(protocol.canonical(identities).encode()).hexdigest(),
                category=value['category'], semantic_reward=value['semantic_reward'],
                terminal_reward_observed=value['native_reward'], finish_reason='stop',
                generation_tokens=generation, observation_tokens=observations, max_context=context))
        return rows, events

    def test_actual_native_replay_with_pinned_accounting(self):
        before = copy.deepcopy((self.rows, self.events))
        result = verify_chunk(self.bundle, self.rows, self.events, self.counter)
        self.assertEqual(len(result['call_ids']), 4)
        self.assertEqual(len(result['response_ids']), 4)
        self.assertLessEqual(result['max_context'], 24576)
        self.assertLessEqual(result['max_completion'], 8192)
        self.assertTrue(all(r['category'] == 'full' for r in self.rows))
        self.assertEqual((self.rows, self.events), before)

    def test_changed_usage_request_identity_grade_and_extra_choice_are_rejected(self):
        for mutation in ('usage', 'request', 'identity', 'grade', 'choices'):
            with self.subTest(mutation=mutation):
                rows, events = copy.deepcopy((self.rows, self.events))
                response = next(e['response'] for e in events if e['event'] == 'response')
                if mutation == 'usage': response['usage']['completion_tokens'] += 1
                elif mutation == 'request': next(e for e in events if e['event'] == 'intent')['request_sha256'] = '0' * 64
                elif mutation == 'identity': response['id'] += '-forged'
                elif mutation == 'grade': rows[0]['semantic_reward'] = .95
                elif mutation == 'choices': response['choices'].append(copy.deepcopy(response['choices'][0]))
                with self.assertRaises(ValueError): verify_chunk(self.bundle, rows, events, self.counter)

    def test_unassigned_events_and_altered_original_bundle_are_rejected(self):
        events = copy.deepcopy(self.events)
        events.append(dict(event='calling', attempt_id='not-assigned', call_id='fictional'))
        with self.assertRaisesRegex(ValueError, 'unassigned event'):
            verify_chunk(self.bundle, self.rows, events, self.counter)
        frozen = copy.deepcopy(self.bundle); frozen['context'] += 1
        with self.assertRaisesRegex(ValueError, 'exact original chunk'):
            verify_chunk(frozen, self.rows, self.events, self.counter)


if __name__ == '__main__': unittest.main()
