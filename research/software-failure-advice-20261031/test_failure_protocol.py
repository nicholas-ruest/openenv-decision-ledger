import argparse,copy,importlib.util,json,os
from pathlib import Path
import unittest
import failure_protocol as p


class MatchedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('matched_failure_counter',p.ROOT/'integrations/openenv-arena/scripts/calibrate.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        cls.counter=m.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=Path(os.environ['HELPER_TEST_TOKENIZER']),tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
    def response(self,text,identity,finish='stop'):
        return dict(id=identity,usage=dict(prompt_tokens=4000,completion_tokens=self.counter.count(text)),choices=[dict(finish_reason=finish,message=dict(role='assistant',content=text))])
    def trace(self,job):
        from repair_env.tasks import make_task
        t=p.QualificationTrial(job);source=json.loads(t.messages[1]['content'])['source']
        return p.observe_scripted(job,[self.response(json.dumps(dict(content=source)),job['attempt_id']+':0'),self.response(json.dumps(dict(content=make_task(p.TASK,3100000).reference_source)),job['attempt_id']+':1')],self.counter)
    def test_all_original_assignments_replay_advice_and_costs(self):
        traces=[self.trace(j) for j in p.jobs('qualification')];report=p.verify_phase(traces,self.counter)
        self.assertEqual(len(report['rows']),8);self.assertFalse(report['selection_passed'])
        for r in report['rows']:
            self.assertEqual(r['category'],'full');self.assertEqual(r['advice_deliveries'],int(r['job']['arm']=='focused_failure_advice'))
            self.assertEqual(r['completion_with_observations'],r['generation_tokens']+r['native_observation_tokens']+r['advice_observation_tokens'])
        with self.assertRaises(ValueError):p.verify_phase(traces[:-1],self.counter)
        bad=copy.deepcopy(traces);bad[1]['events'][0]['response']['id']=bad[0]['events'][0]['response']['id']
        with self.assertRaises(ValueError):p.verify_phase(bad,self.counter)
    def test_actual_pinned_fitness_on_complete_qualification_cannot_select_live(self):
        import subprocess
        report=p.verify_phase([self.trace(j) for j in p.jobs('qualification')],self.counter)
        module=Path(__file__).with_name('assess_qualification.mjs').as_uri()
        js="import {readFileSync} from 'node:fs';import {assess} from "+json.dumps(module)+";console.log(JSON.stringify(assess(JSON.parse(readFileSync(0,'utf8')))));"
        def score(value):
            out=subprocess.run(['node','--input-type=module','-e',js],input=json.dumps(value),text=True,capture_output=True,check=True)
            return json.loads(out.stdout)
        result=score(report)
        self.assertEqual(result['actual_module'],'fitness.mjs:scoreCell')
        self.assertEqual(result['metaharness_source'],'b8c3d38de41203faf633ef6dceb8452a4727b0ea')
        self.assertEqual(result['groups'][1]['advice_deliveries'],4);self.assertFalse(result['selection_passed'])
        for kind in ('cost','live','missing'):
            bad=copy.deepcopy(report)
            if kind=='cost':bad['rows'][1]['advice_observation_tokens']=0
            elif kind=='live':bad['scripted']=False;bad['live_evidence']=True
            else:bad['rows'].pop()
            with self.subTest(kind=kind),self.assertRaises(subprocess.CalledProcessError):score(bad)

    def test_same_first_prompt_and_sampling_no_future_materialization(self):
        a,b=p.jobs('qualification')[:2]
        self.assertEqual(p.QualificationTrial(a).messages,p.QualificationTrial(b).messages)
        for turn in (0,1):self.assertEqual(p.sampling_for(a,turn),p.sampling_for(b,turn))
        self.assertEqual(p.sampling_for(a,0),p.sampling_for(a,1))
        self.assertNotIn('chat_template_kwargs',p.SAMPLING)
        for j in p.jobs('screen')+p.jobs('confirmation'):
            with self.assertRaises(ValueError):p.materialize(j)
            with self.assertRaises(ValueError):p.QualificationTrial(j)
    def test_exposure_prompt_cost_grade_and_live_relabelling_tampering_rejected(self):
        trace=self.trace(p.jobs('qualification')[1])
        for kind in ('advice','prompt','cost','grade','live'):
            bad=copy.deepcopy(trace)
            if kind=='advice':bad['events'][0]['advice_observations']=[]
            elif kind=='prompt':bad['events'][1]['prompt_sha256']='a'*64
            elif kind=='cost':bad['record']['advice_observation_tokens']=0
            elif kind=='grade':bad['record']['semantic_reward']=0
            else:bad['scripted']=False;bad['live_evidence']=True
            with self.subTest(kind=kind),self.assertRaises(ValueError):p.verify(bad,self.counter)
    def test_unknown_usage_truncation_incomplete_and_duplicate_replies(self):
        j=p.jobs('qualification')[1];r=self.response('unfinished','one','length')
        t=p.observe_scripted(j,[r],self.counter)
        self.assertEqual(p.verify(t,self.counter)['category'],'truncation');self.assertEqual(t['record']['advice_deliveries'],0)
        r['usage']['completion_tokens']=None
        with self.assertRaises(ValueError):p.observe_scripted(j,[r],self.counter)
        trace=self.trace(j)
        with self.assertRaises(ValueError):p.observe_scripted(j,[trace['events'][0]['response']],self.counter)
        with self.assertRaises(ValueError):p.observe_scripted(j,[e['response'] for e in trace['events']]+[trace['events'][0]['response']],self.counter)


if __name__=='__main__':unittest.main()
