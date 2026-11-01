import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import matched_note as p


class MatchedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p.n.Binding(p.n.job('baseline'))
        sys.path.insert(0,str(p.n.ROOT/'integrations/openenv-arena'))
        module=p.n.original.load('top_level_matched_counter','integrations/openenv-arena/scripts/calibrate.py')
        cls.counter=module.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=Path(os.environ['HELPER_TEST_TOKENIZER']),
            tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
        from repair_env.tasks import make_task
        task=make_task(p.n.original.TASK,p.n.original.QUALIFICATION_SEED)
        scripts=[(json.dumps(dict(content=task.reference_source)),'stop'),
                 ('{"content":"def classify_ignore(path, rules):\\n    def helper(x): return x\\n    return helper(False)"}','stop'),
                 ('{"content":"def classify_ignore(path, rules): return 1 // 0"}','stop'),
                 (json.dumps(dict(content=task.initial_source)),'stop'),
                 ('unfinished','length'),('invalid json','stop'),('unfinished','length'),('{}','error')]
        cls.traces=[]
        for i,(job,(text,finish)) in enumerate(zip(p.jobs('qualification'),scripts)):
            response=dict(id='syntax-qualification:'+str(i),usage=dict(prompt_tokens=4000,completion_tokens=cls.counter.count(text)),choices=[dict(finish_reason=finish,message=dict(role='assistant',content=text))])
            cls.traces.append(p.observe(job,response,cls.counter))

    def test_all_original_samples_replay_without_promoting_program_errors(self):
        report=p.verify_phase(self.traces,self.counter)
        self.assertEqual(report['rows'][1]['category'],'execution')
        self.assertEqual(report['rows'][1]['failure_origin'],'model_program_rejection')
        self.assertEqual(report['rows'][1]['terminal_reward_observed'],0)
        self.assertIsNone(report['rows'][1]['semantic_reward'])
        self.assertEqual(report['rows'][2]['failure_origin'],'model_program_runtime_error')
        self.assertEqual(report['assigned'],8);self.assertFalse(report['selection_passed'])
        for kind in ('origin','live','reply','missing'):
            bad=copy.deepcopy(self.traces)
            if kind=='origin':bad[1]['record']['failure_origin']='native_semantic_outcome'
            elif kind=='live':bad[1]['scripted']=False;bad[1]['live_evidence']=True
            elif kind=='reply':bad[1]['response']['id']=bad[0]['response']['id']
            else:bad.pop()
            with self.assertRaises(ValueError):p.verify_phase(bad,self.counter)

    def test_actual_pinned_fitness_keeps_model_program_errors_fail_closed(self):
        report=p.verify_phase(self.traces,self.counter)
        module=Path(__file__).with_name('assess_qualification.mjs').as_uri()
        js="import {readFileSync} from 'node:fs';import {assess} from "+json.dumps(module)+";console.log(JSON.stringify(assess(JSON.parse(readFileSync(0,'utf8')))));"
        def score(value):
            return json.loads(subprocess.run(['node','--input-type=module','-e',js],input=json.dumps(value),text=True,capture_output=True,check=True).stdout)
        result=score(report)
        self.assertEqual(result['metaharness_source'],'b8c3d38de41203faf633ef6dceb8452a4727b0ea')
        self.assertEqual(result['actual_module'],'fitness.mjs:scoreCell');self.assertFalse(result['selection_passed'])
        self.assertEqual(sum(x['model_program_failures'] for x in result['groups']),2)
        for kind in ('reward','proof','live'):
            bad=copy.deepcopy(report)
            if kind=='reward':bad['rows'][1]['semantic_reward']=0
            elif kind=='proof':bad['rows'][1]['native_compile_rejected']=False
            else:bad['scripted']=False;bad['live_evidence']=True
            with self.assertRaises(subprocess.CalledProcessError):score(bad)

    def test_future_plan_cannot_generate_inputs(self):
        with patch.object(p.n,'QualificationTrial',side_effect=AssertionError('no capture')):
            plan=p.plan()
            for job in p.jobs('screen')+p.jobs('confirmation'):
                with self.assertRaises(ValueError):p.observe(job,self.traces[0]['response'],self.counter)
        self.assertEqual(len(plan['screen_jobs']),8);self.assertFalse(plan['live_execution_ready'])
        self.assertFalse(plan['confirmation_materialized'])


if __name__=='__main__':unittest.main()
