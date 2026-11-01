import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import matched_protocol as p


class MatchedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p.native.QualificationBinding(p.native.qualification_job('baseline'))
        sys.path.insert(0, str(p.native.ROOT / 'integrations/openenv-arena'))
        module = p.native.load('preserve_matched_counter', 'integrations/openenv-arena/scripts/calibrate.py')
        cls.counter = module.load_counter(argparse.Namespace(accounting='arena',
            tokenizer_json=Path(os.environ['HELPER_TEST_TOKENIZER']),
            tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
        from repair_env.tasks import make_task
        task = make_task(p.native.TASK, p.native.QUALIFICATION_SEED)
        replies = [(json.dumps({'content': task.reference_source}), 'stop'),
                   (json.dumps({'content': task.initial_source}), 'stop'),
                   ('incomplete', 'length'), ('invalid json', 'stop'),
                   ('{"content":"import os"}', 'stop'), ('{}', 'error'),
                   ('incomplete', 'length'), ('invalid json', 'stop')]
        cls.responses = [dict(id='scripted-preserve:'+str(i),
            usage=dict(prompt_tokens=4000, completion_tokens=cls.counter.count(text)),
            choices=[dict(finish_reason=finish, message=dict(role='assistant', content=text))])
            for i, (text, finish) in enumerate(replies)]
        cls.traces = [p.observe_scripted(j, r, cls.counter) for j, r in zip(p.jobs('qualification'), cls.responses)]

    def test_all_original_assignments_replay_with_failures_and_observations_in_denominator(self):
        report = p.verify_phase(self.traces, self.counter)
        self.assertEqual([r['category'] for r in report['rows']],
                         ['full','wrong','truncation','format','execution','provider','truncation','format'])
        self.assertFalse(report['selection_passed'])
        for row in report['rows']:
            self.assertEqual(row['completion_with_observations'], row['generation_tokens'] + row['native_observation_tokens'])
            self.assertEqual(row['model_responses'], 1)
        self.assertGreater(report['rows'][0]['native_observation_tokens'], 0)
        self.assertEqual(report['rows'][2]['native_observation_tokens'], 0)

    def test_missing_reordered_and_reused_replies_rejected(self):
        variants = [self.traces[:-1], list(reversed(self.traces))]
        bad = copy.deepcopy(self.traces);bad[1]['response']['id'] = bad[0]['response']['id'];variants.append(bad)
        for value in variants:
            with self.assertRaises(ValueError): p.verify_phase(value, self.counter)

    def test_tampered_prompt_grade_cost_and_live_relabelling_rejected(self):
        for field, value in [('request_sha256', 'f'*64), ('observations', []),
                              ('scripted', False), ('live_evidence', True)]:
            trace = copy.deepcopy(self.traces[0]);trace[field] = value
            with self.assertRaises(ValueError): p.verify(trace, self.counter)
        for field, value in [('semantic_reward', 0), ('native_observation_tokens', 0),
                              ('controller_actions', ['restored helper'])]:
            trace = copy.deepcopy(self.traces[0]);trace['record'][field] = value
            with self.assertRaises(ValueError): p.verify(trace, self.counter)

    def test_actual_usage_and_context_bounds_and_unknown_usage_are_not_invented(self):
        for key, value in [('completion_tokens', None), ('completion_tokens', 6001),
                            ('prompt_tokens', 24576)]:
            response = copy.deepcopy(self.responses[0]);response['usage'][key] = value
            with self.assertRaises(ValueError): p.observe_scripted(p.jobs('qualification')[0], response, self.counter)

    def test_plan_does_not_materialize_future_inputs(self):
        with patch.object(p.native, 'QualificationTrial', side_effect=AssertionError('no capture')):
            plan = p.plan()
            self.assertEqual(plan['max_requests'], 8)
            self.assertFalse(plan['live_execution_ready'])
            for phase in ('screen', 'confirmation'):
                for job in p.jobs(phase):
                    with self.assertRaises(ValueError): p.observe_scripted(job, self.responses[0], self.counter)
        self.assertEqual([j['arm'] for j in p.jobs('screen')[:4]], ['baseline','preserve_supplied','preserve_supplied','baseline'])
        self.assertFalse(set(j['seed'] for j in p.jobs('screen')) & set(j['seed'] for j in p.jobs('confirmation')))

    def test_actual_pinned_fitness_executes_but_cannot_select_scripted_results(self):
        report = p.verify_phase(self.traces, self.counter)
        module = Path(__file__).with_name('assess_qualification.mjs').as_uri()
        js = "import {readFileSync} from 'node:fs';import {assess} from "+json.dumps(module)+";console.log(JSON.stringify(assess(JSON.parse(readFileSync(0,'utf8')))));"
        def score(value):
            result = subprocess.run(['node','--input-type=module','-e',js],
                input=json.dumps(value), text=True, capture_output=True, check=True)
            return json.loads(result.stdout)
        scored = score(report)
        self.assertEqual(scored['metaharness_source'], 'b8c3d38de41203faf633ef6dceb8452a4727b0ea')
        self.assertEqual(scored['actual_module'], 'fitness.mjs:scoreCell')
        self.assertFalse(scored['selection_passed'])
        self.assertEqual(scored['groups'][0]['categories']['execution'], 1)
        for mode in ('missing', 'cost', 'live'):
            bad = copy.deepcopy(report)
            if mode == 'missing': bad['rows'].pop()
            elif mode == 'cost': bad['rows'][0]['native_observation_tokens'] = 0
            else: bad['scripted'] = False;bad['live_evidence'] = True
            with self.assertRaises(subprocess.CalledProcessError): score(bad)


if __name__ == '__main__': unittest.main()
