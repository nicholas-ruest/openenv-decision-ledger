"""Existing-case Native qualification; scripted responses are never model solves."""
import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import matched_protocol as p
from replay_matched import verify


class MatchedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('helper_matched_counter', p.ROOT/'integrations/openenv-arena/scripts/calibrate.py')
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        cls.counter = m.load_counter(argparse.Namespace(accounting='arena',
            tokenizer_json=Path(os.environ['HELPER_TEST_TOKENIZER']),
            tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
        from repair_env.tasks import make_task
        source = make_task(p.TASK, 3100000).reference_source
        cls.content = source.replace('return table[len(tokens)][len(word)]', 'return False')
        cls.traces = {}
        for job in p.jobs('qualification')[:2]:
            trial = p.QualificationTrial(job); responses = []
            for content in (cls.content, ''):
                text = json.dumps(dict(content=content))
                responses.append(dict(usage=dict(prompt_tokens=cls.counter.context(trial.messages),
                    completion_tokens=cls.counter.count(text)),
                    choices=[dict(finish_reason='stop', message=dict(role='assistant', content=text))]))
                trial.consume(text)
            cls.traces[job['arm']] = p.observe_scripted(job, responses, cls.counter)

    def test_matched_initial_prompts_and_no_future_materialization(self):
        a,b = p.jobs('qualification')[:2]
        self.assertEqual(p.QualificationTrial(a).messages, p.QualificationTrial(b).messages)
        with patch.object(p, 'QualificationTrial', side_effect=AssertionError('no Native capture')):
            plan = p.plan()
            self.assertFalse(plan['paid_execution_ready'])
            self.assertIsNone(plan['live_case_lease'])
            self.assertEqual(len(plan['screen_jobs']), 8)
            self.assertEqual(len(plan['confirmation_jobs']), 8)
            for job in plan['screen_jobs']+plan['confirmation_jobs']:
                with self.assertRaises(ValueError): p.materialize(job)
        with self.assertRaises(ValueError):p.QualificationTrial(p.jobs('screen')[0])

    def test_native_outcomes_and_actual_receipt_budget_replay(self):
        for arm, trace in self.traces.items():
            proof = verify(trace, self.counter)
            self.assertTrue(proof['verified'])
            self.assertFalse(proof['live_evidence'])
            self.assertEqual(proof['completion_with_observations'], proof['generation_tokens']+
                             proof['native_observation_tokens']+proof['controller_observation_tokens'])
        c = self.traces['preserve_declared_helpers']['record']
        self.assertEqual(c['category'], 'full')
        self.assertTrue(c['controller_assisted_full'])
        self.assertFalse(c['model_response_only_full'])
        self.assertGreater(c['controller_observation_tokens'], 0)
        self.assertNotEqual(self.traces['standard_revision']['record']['category'], 'full')
        trial=p.QualificationTrial(p.jobs('qualification')[1])
        result=trial.consume(json.dumps(dict(content=self.content)))
        self.assertEqual(trial.messages[-1]['content'],p.canonical(result['controller_observations'][0]))

    def test_provenance_receipt_and_outcome_tampering_rejected(self):
        trace = self.traces['preserve_declared_helpers']
        for change in ('receipt_cost','authorship','prompt','grade'):
            bad = copy.deepcopy(trace)
            if change=='receipt_cost':bad['record']['controller_observation_tokens']=0
            elif change=='authorship':bad['events'][0]['controller_actions'][0]['authored_by']='model'
            elif change=='prompt':bad['events'][1]['prompt_sha256']='0'*64
            else:bad['events'][0]['native_observations'][0]['reward']=1
            with self.subTest(change=change),self.assertRaises(ValueError):verify(bad,self.counter)

    def test_truncated_reply_has_no_native_or_controller_recovery(self):
        job=p.jobs('qualification')[1]
        response=copy.deepcopy(self.traces[job['arm']]['events'][0]['response'])
        response['usage']['completion_tokens']=6000
        response['choices'][0]['finish_reason']='length'
        trace=p.observe_scripted(job,[response],self.counter)
        self.assertEqual(verify(trace,self.counter)['category'],'truncation')
        bad=copy.deepcopy(trace);bad['events'][0]['controller_actions']=[dict(authored_by='controller')]
        with self.assertRaises(ValueError):verify(bad,self.counter)

    def test_incomplete_unknown_usage_and_extra_responses_refused(self):
        trace=self.traces['standard_revision'];job=trace['job']
        first=trace['events'][0]['response']
        incomplete=p.observe_scripted(job,[first],self.counter)
        with self.assertRaises(ValueError):verify(incomplete,self.counter)
        unknown=copy.deepcopy(first);unknown['usage']['completion_tokens']=None
        with self.assertRaises(ValueError):p.observe_scripted(job,[unknown],self.counter)
        bad=copy.deepcopy(trace);bad['events'].append(copy.deepcopy(bad['events'][-1]))
        with self.assertRaises(ValueError):verify(bad,self.counter)
        bad=copy.deepcopy(trace);bad['scripted']=False
        with self.assertRaises(ValueError):verify(bad,self.counter)


if __name__=='__main__':unittest.main()
