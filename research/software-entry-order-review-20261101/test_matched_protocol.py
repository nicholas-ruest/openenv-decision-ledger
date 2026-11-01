import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import subprocess
import unittest
from unittest.mock import patch
import matched_protocol as p
import test_order_review as fixtures


class MatchedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.OrderTests.setUpClass();cls.fixture=fixtures.OrderTests
        sys.path.insert(0,str(p.d.ROOT/'integrations/openenv-arena'))
        spec=importlib.util.spec_from_file_location('matched_order_counter',p.d.ROOT/'integrations/openenv-arena/scripts/calibrate.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        cls.counter=module.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=Path(os.environ['HELPER_TEST_TOKENIZER']),tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
        cls.traces=[]
        for job in p.jobs('qualification'):
            trial=p.Trial(job);responses=[]
            final=cls.fixture.good if job['sample']<2 else cls.fixture.constant_wrong
            for turn,code in enumerate((cls.fixture.order_bug,final)):
                finish='stop'
                if turn==1 and job['sample']==3:finish='length' if job['arm']==p.d.ARMS[0] else 'error'
                message=dict(role='assistant',content=json.dumps(dict(content=code)))
                response=dict(id='scripted-'+job['attempt_id']+':'+str(turn),usage=dict(prompt_tokens=cls.counter.context(trial.messages),completion_tokens=cls.counter.count(message['content'])),choices=[dict(finish_reason=finish,message=message)])
                responses.append(response);trial.consume(message,finish)
            cls.traces.append(p.observe(job,responses,cls.counter))

    def test_all_original_assignments_replay_native_costs_and_exposure(self):
        result=p.verify_phase(self.traces,self.counter)
        self.assertTrue(result['scripted']);self.assertFalse(result['selection_passed']);self.assertEqual(len(result['rows']),8)
        self.assertEqual(len({t['requests'][0]['messages'][1]['content'] for t in self.traces}),1)
        for t in self.traces:
            row=t['record'];self.assertEqual(row['model_responses'],2)
            self.assertEqual(row['computed_relation_exposed'],t['job']['arm']=='computed_relation')
            self.assertEqual(row['usable_relation_counterexample_exposed'],t['job']['arm']=='computed_relation')
            self.assertEqual(row['completion_with_observations'],row['generation_tokens']+row['native_observation_tokens'])
            self.assertLessEqual(row['completion_with_observations'],8192)
            self.assertEqual(t['steps'][1]['generation_limit'],min(8096,8192-t['steps'][0]['generation_tokens']-t['steps'][0]['native_observation_tokens']-96))
        self.assertEqual(self.traces[-2]['record']['category'],'provider')
        self.assertEqual(self.traces[-1]['record']['category'],'truncation')

    def test_tampered_review_requests_usage_and_reused_replies_are_refused(self):
        for field in ('messages','requests','responses','record'):
            bad=copy.deepcopy(self.traces[0])
            if field=='record':bad['record']['native_observation_tokens']=0
            elif field=='responses':bad['responses'][0]['usage']['completion_tokens']=6001
            elif field=='messages':bad['messages'][3]['content']='fake review'
            else:bad['requests'][1]['messages'][3]['content']='fake review'
            with self.assertRaises(ValueError):p.verify(bad,self.counter)
        bad=copy.deepcopy(self.traces);bad[1]['responses'][0]['id']=bad[0]['responses'][0]['id']
        with self.assertRaises(ValueError):p.verify_phase(bad,self.counter)
        with self.assertRaises(ValueError):p.observe(p.jobs('qualification')[0],self.traces[0]['responses'][:1],self.counter)

    def test_actual_pinned_metaharness_runs_on_scripted_denominator_only(self):
        value=p.verify_phase(self.traces,self.counter)
        module=Path(__file__).with_name('assess_qualification.mjs').as_uri()
        js="import {readFileSync} from 'node:fs';import {assess} from "+json.dumps(module)+";console.log(JSON.stringify(assess(JSON.parse(readFileSync(0,'utf8')))));"
        result=subprocess.run(['node','--input-type=module','-e',js],input=json.dumps(value),text=True,capture_output=True,check=True)
        score=json.loads(result.stdout);self.assertEqual(score['actual_module'],'fitness.mjs:scoreCell')
        self.assertFalse(score['selection_passed']);self.assertFalse(score['live_evidence'])
        self.assertEqual([g['computed_relation_exposures'] for g in score['groups']],[0,4])
        value['live_evidence']=True
        bad=subprocess.run(['node','--input-type=module','-e',js],input=json.dumps(value),text=True,capture_output=True)
        self.assertNotEqual(bad.returncode,0)

    def test_future_jobs_and_actual_observation_overruns_stay_fail_closed(self):
        with self.assertRaises(ValueError):p.Trial(p.jobs('screen')[0])
        with patch.object(p,'Trial',side_effect=AssertionError('plan must not capture cases')):plan=p.plan()
        self.assertFalse(plan['live_execution_ready']);self.assertEqual(len(plan['screen_jobs']),8)
        job=self.traces[0]['job'];responses=copy.deepcopy(self.traces[0]['responses'])
        responses[0]['usage']['prompt_tokens']=24576-responses[0]['usage']['completion_tokens']
        with self.assertRaises(ValueError):p.observe(job,responses,self.counter)
        response=copy.deepcopy(self.traces[0]['responses'][0]);response['choices'][0]['message']['content']='invalid'
        trace=p.observe(job,[response],self.counter);self.assertEqual(trace['record']['category'],'format')
        self.assertIsNone(trace['record']['semantic_reward'])
        response['choices'][0]['finish_reason']='length'
        self.assertEqual(p.observe(job,[response],self.counter)['record']['category'],'truncation')


if __name__=='__main__':unittest.main()
