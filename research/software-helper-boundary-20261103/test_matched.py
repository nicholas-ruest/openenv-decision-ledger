import argparse, copy, importlib.util, json, os, subprocess, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import matched_protocol as p

WRONG = 'def classify_ignore(ignore_lines, entries):\n    return {}\n'


class AccountingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(p.r.ROOT / 'integrations/openenv-arena'))
        path = p.r.ROOT / 'integrations/openenv-arena/scripts/calibrate.py'
        spec = importlib.util.spec_from_file_location('boundary_token_counter', path)
        helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
        cls.counter = helper.load_counter(argparse.Namespace(accounting='arena',
            tokenizer_json=Path(os.environ['HELPER_TEST_TOKENIZER']),
            tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
        cls.traces = []
        for job in p.jobs():
            trial, responses = p.Trial(job), []
            for turn in range(2):
                content, finish = json.dumps({'content': WRONG if turn == 0 else ''}), 'stop'
                if turn == 1 and job['sample'] == 1:
                    content = json.dumps({'content':'import os'})
                if turn == 1 and job['sample'] == 2:
                    content = 'not JSON'
                if turn == 1 and job['sample'] == 3:
                    finish = 'length'
                message = {'role':'assistant','content':content}
                responses.append({'id':'scripted-'+job['attempt_id']+':'+str(turn),
                    'usage':{'prompt_tokens':cls.counter.context(trial.messages),
                             'completion_tokens':cls.counter.count(content)},
                    'choices':[{'message':message,'finish_reason':finish}]})
                trial.consume(message,finish)
            cls.traces.append(p.observe(job,responses,cls.counter))

    def test_actual_feedback_tokens_and_second_generation_limit_replay(self):
        value = p.verify_phase(self.traces,self.counter)
        self.assertEqual(len(value['rows']),8)
        self.assertEqual(len({t['prompt_sha256'] for t in self.traces}),1)
        self.assertEqual(len({t['problem_sha256'] for t in self.traces}),1)
        costs = {}
        for trace in self.traces:
            row, first = trace['record'], trace['steps'][0]
            self.assertEqual(row['completion_with_observations'],row['generation_tokens']+row['native_observation_tokens'])
            self.assertEqual(trace['steps'][1]['generation_limit'],min(8096,8192-first['generation_tokens']-first['native_observation_tokens']-96))
            self.assertEqual(row['helper_input_boundary_exposed'],trace['job']['arm']=='helper_input_boundary')
            self.assertFalse(row['computed_relation_exposed'])
            if trace['job']['sample']==0:costs[trace['job']['arm']]=first['native_observation_tokens']
        self.assertGreater(costs['helper_input_boundary'],costs['common_review'])

    def test_changed_feedback_usage_and_incomplete_phase_refused(self):
        for field in ('messages','record','responses'):
            trace=copy.deepcopy(self.traces[1])
            if field=='messages':trace[field][3]['content']='altered review'
            elif field=='record':trace[field]['native_observation_tokens']-=1
            else:trace[field][0]['usage']['completion_tokens']+=1
            with self.assertRaises(ValueError):p.verify(trace,self.counter)
        with self.assertRaises(ValueError):p.verify_phase(self.traces[:-1],self.counter)
        for phase in ('screen','confirmation'):
            with self.assertRaises(ValueError):p.jobs(phase)

    def test_actual_pinned_metaharness_preserves_all_assignments_without_selection(self):
        value=p.verify_phase(self.traces,self.counter)
        module=Path(__file__).with_name('assess_qualification.mjs').as_uri()
        js="import {readFileSync} from 'node:fs';import {assess} from "+json.dumps(module)+";console.log(JSON.stringify(assess(JSON.parse(readFileSync(0,'utf8')))));"
        run=subprocess.run(['node','--input-type=module','-e',js],input=json.dumps(value),text=True,capture_output=True,check=True)
        result=json.loads(run.stdout)
        self.assertEqual(result['actual_module'],'fitness.mjs:scoreCell')
        self.assertEqual([g['assigned'] for g in result['groups']],[4,4])
        self.assertEqual([g['reminder_exposures'] for g in result['groups']],[0,4])
        self.assertFalse(result['selection_passed'])
        self.assertFalse(result['model_improvement'])


if __name__=='__main__':unittest.main()
