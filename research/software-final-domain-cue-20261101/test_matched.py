import argparse,copy,importlib.util,json,os,subprocess,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import matched_protocol as p
from repair_env.tasks import make_task

class ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0,str(p.r.ROOT/'integrations/openenv-arena'))
        task=make_task('software_repair-ignore-d3',2560000);cls.good=task.reference_source
        cls.extra=cls.good.replace('    return result\n','    result["extra_internal_path"] = False\n    return result\n')
        spec=importlib.util.spec_from_file_location('domain_counter',p.r.ROOT/'integrations/openenv-arena/scripts/calibrate.py')
        helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
        cls.counter=helper.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=Path(os.environ['HELPER_TEST_TOKENIZER']),tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
        cls.traces=[]
        for job in p.jobs():
            trial=p.Trial(job);responses=[]
            for turn in range(2):
                code=cls.good if turn==0 or job['sample']==0 else cls.extra if job['sample']==1 else 'import os'
                message=dict(role='assistant',content=json.dumps(dict(content=code)))
                finish='stop'
                if turn==1 and job['sample']==3:
                    if job['arm']=='common_review':message['content']='not JSON'
                    else:finish='length'
                response=dict(id='scripted-'+job['attempt_id']+':'+str(turn),usage=dict(prompt_tokens=cls.counter.context(trial.messages),completion_tokens=cls.counter.count(message['content'])),choices=[dict(message=message,finish_reason=finish)])
                responses.append(response);trial.consume(message,finish)
            cls.traces.append(p.observe(job,responses,cls.counter))

    def test_original_requests_native_outcomes_and_all_feedback_costs_replay(self):
        value=p.verify_phase(self.traces,self.counter)
        self.assertEqual(len(value['rows']),8);self.assertFalse(value['live_evidence'])
        self.assertEqual(len({t['prompt_sha256'] for t in self.traces}),1)
        for trace in self.traces:
            row=trace['record'];self.assertEqual(row['final_domain_reminder_exposed'],trace['job']['arm']=='final_domain_reminder')
            self.assertEqual(row['completion_with_observations'],row['generation_tokens']+row['native_observation_tokens'])
            first=trace['steps'][0]
            self.assertEqual(trace['steps'][1]['generation_limit'],min(8096,8192-first['generation_tokens']-first['native_observation_tokens']-96))
            if trace['job']['sample']==1:self.assertEqual(row['category'],'partial');self.assertLess(row['semantic_reward'],1)
            if trace['job']['sample']==2:self.assertEqual(row['category'],'execution');self.assertIsNone(row['semantic_reward'])
        feedback=[json.loads(t['steps'][0]['result']['new_observations'][0]['feedback']) for t in self.traces[:2]]
        feedback[1].pop('final_output_domain_reminder');self.assertEqual(*feedback)

    def test_tampered_request_feedback_usage_exposure_and_reuse_refused(self):
        for field in ['requests','messages','record','responses']:
            t=copy.deepcopy(self.traces[1])
            if field=='requests':t[field][1]['temperature']=0
            elif field=='messages':t[field][3]['content']='fake feedback'
            elif field=='record':t[field]['final_domain_reminder_exposed']=False
            else:t[field][0]['usage']['completion_tokens']=6001
            with self.assertRaises(ValueError):p.verify(t,self.counter)
        traces=copy.deepcopy(self.traces);traces[1]['responses'][0]['id']=traces[0]['responses'][0]['id']
        with self.assertRaises(ValueError):p.verify_phase(traces,self.counter)
        with self.assertRaises(ValueError):p.verify_phase(self.traces[:-1],self.counter)

    def test_first_response_failure_never_claims_review_exposure(self):
        response=copy.deepcopy(self.traces[1]['responses'][0]);response['choices'][0]['finish_reason']='length'
        trace=p.observe(p.jobs()[1],[response],self.counter);row=p.verify(trace,self.counter)
        self.assertFalse(row['final_domain_reminder_exposed']);self.assertFalse(row['final_domain_reminder_presented'])
        self.assertEqual(row['category'],'truncation')

    def assess(self,value,check=True):
        module=Path(__file__).with_name('assess_qualification.mjs').as_uri()
        js="import {readFileSync} from 'node:fs';import {assess} from "+json.dumps(module)+";console.log(JSON.stringify(assess(JSON.parse(readFileSync(0,'utf8')))));"
        return subprocess.run(['node','--input-type=module','-e',js],input=json.dumps(value),text=True,capture_output=True,check=check)

    def test_actual_pinned_metaharness_keeps_failures_and_scripted_no_selection(self):
        value=p.verify_phase(self.traces,self.counter);result=json.loads(self.assess(value).stdout)
        self.assertEqual(result['actual_module'],'fitness.mjs:scoreCell');self.assertFalse(result['selection_passed'])
        self.assertEqual([r['reminder_exposures'] for r in result['groups']],[0,4])
        self.assertTrue(all(r['infra']>=1 for r in result['groups']))
        for field in ['live_evidence','scripted']:
            bad=copy.deepcopy(value);bad[field]=not bad[field]
            self.assertNotEqual(self.assess(bad,check=False).returncode,0)

    def test_no_live_case_or_sampling_change(self):
        self.assertEqual(p.SAMPLING,p.p.SAMPLING)
        for phase in ['screen','confirmation']:
            with self.assertRaises(ValueError):p.jobs(phase)
        job=copy.deepcopy(p.jobs()[0]);job['seed']+=1
        with self.assertRaises(ValueError):p.Trial(job)
        trace=copy.deepcopy(self.traces[0]);trace['live_evidence']=True
        with self.assertRaises(ValueError):p.verify(trace,self.counter)

if __name__=='__main__':unittest.main()
