"""Synthetic interrupted archives, actual already-seen Native fixture, mocked gate."""
import argparse,copy,importlib.util,json,os,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import case_replay as r


class PrefixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jobs=r.binding.gate.jobs_for(dict(task_id='software_repair-ignore-d3',new_seed=2560000));cls.job=cls.jobs[1]
        cls.args=SimpleNamespace(expected_source='0'*40)
        cls.gate=patch.object(r.binding.gate,'require_case',return_value=dict(jobs=cls.jobs,case_audit_sha256='a'*64));cls.gate.start();cls.addClassCleanup(cls.gate.stop)
        runtime=r.binding._runtime();root=runtime.r.ROOT;sys.path.insert(0,str(root/'integrations/openenv-arena'))
        spec=importlib.util.spec_from_file_location('prefix_actual_counter',root/'integrations/openenv-arena/scripts/calibrate.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
        cls.counter=helper.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=Path(os.environ['HELPER_TEST_TOKENIZER']),tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
        from repair_env.tasks import make_task
        source=make_task('software_repair-ignore-d3',2560000).reference_source
        trial=r.binding.materialize(cls.job,cls.args);message=dict(role='assistant',content=json.dumps(dict(content=source)))
        cls.response=dict(id='synthetic-prefix-known',usage=dict(prompt_tokens=cls.counter.context(trial.messages),completion_tokens=cls.counter.count(message['content'])),choices=[dict(message=message,finish_reason='stop')])
        cls.requests=[dict(copy.deepcopy(runtime.SAMPLING),messages=copy.deepcopy(trial.messages),max_tokens=6000)]
        result=trial.consume(message,'stop');observed=sum(cls.counter.count(runtime.p.d.canonical(x)) for x in result['new_observations'])
        limit=min(8096,8192-cls.response['usage']['completion_tokens']-observed-96)
        cls.requests.append(dict(copy.deepcopy(runtime.SAMPLING),messages=copy.deepcopy(trial.messages),max_tokens=limit))
        labels=[cls.job['attempt_id']+':'+str(t) for t in range(2)]
        cls.events=[]
        for turn in range(2):
            cls.events.extend([dict(event='reserved',label=labels[turn]),dict(event='calling',label=labels[turn],request_sha256=runtime.p.digest(cls.requests[turn]),generation_limit=cls.requests[turn]['max_tokens'])])
            if turn==0:cls.events.append(dict(event='response_received',response_id=cls.response['id']))
        cls.row=dict(job=cls.job,reservations=labels,calls=labels,response_ids=[cls.response['id']],category='provider',semantic_reward=None,unknown_usage=True,generation_tokens=None,known_generation_tokens=cls.response['usage']['completion_tokens'])

    def archive(self,path):
        for turn in range(2):(path/('request-'+str(turn)+'.json')).write_text(json.dumps(self.requests[turn]))
        (path/'response-0.json').write_text(json.dumps(self.response))

    def check(self,path,events=None,row=None,seen=None):
        return r.reconstruct_failure_prefix(self.job,path,self.events if events is None else events,self.row if row is None else row,self.counter,self.args,set() if seen is None else seen)

    def test_known_prefix_retained_unknown_total_and_terminal_stay_unobserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);self.archive(path);before=copy.deepcopy(self.row);result=self.check(path)
            self.assertEqual(result['known_prefix_responses_replayed'],1);self.assertGreater(result['known_generation_tokens'],0)
            self.assertTrue(result['unknown_usage']);self.assertIsNone(result['total_generation_tokens']);self.assertIsNone(result['reconstructed_terminal_reward'])
            self.assertFalse(result['provider_provenance_attested']);self.assertFalse(result['execution_authorized']);self.assertFalse(result['selection_passed']);self.assertEqual(self.row,before)

    def test_zeroed_unknown_or_terminal_credit_refused(self):
        for change in [dict(generation_tokens=0),dict(unknown_usage=False),dict(unknown_usage=1),dict(semantic_reward=1),dict(known_generation_tokens=0)]:
            with self.subTest(change=change),tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp);self.archive(path)
                with self.assertRaises(ValueError):self.check(path,row=dict(self.row,**change))

    def test_bad_order_stray_reply_and_reused_identity_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);self.archive(path);events=copy.deepcopy(self.events);events[2],events[3]=events[3],events[2]
            with self.assertRaises(ValueError):self.check(path,events=events)
            with self.assertRaises(ValueError):self.check(path,seen={self.response['id']})
            (path/'response-1.json').write_text(json.dumps(self.response))
            with self.assertRaises(ValueError):self.check(path)

    def test_unknown_second_request_cannot_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);self.archive(path);value=copy.deepcopy(self.requests[1]);value['max_tokens']-=1
            (path/'request-1.json').write_text(json.dumps(value))
            with self.assertRaises(ValueError):self.check(path)

    def test_unsealed_refuses_before_runtime(self):
        self.gate.stop()
        try:
            with patch.object(r.binding,'_runtime',side_effect=AssertionError('Native import')):
                with self.assertRaisesRegex(ValueError,'unsealed'):r.reconstruct_failure_prefix({},None,[],{},None,None,set())
        finally:self.gate.start()

    def test_shared_core_refuses_call_after_terminal_and_exhausted_context(self):
        spec=importlib.util.spec_from_file_location('prefix_core_checks',Path(__file__).with_name('prefix_replay.py'));core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
        for finished,context in [(True,0),(False,24576)]:
            with self.subTest(finished=finished),self.assertRaises(ValueError):
                core.verify_known_prefix({},None,[dict(event='calling')],{},SimpleNamespace(context=lambda _:context),set(),trial=SimpleNamespace(finished=finished,turn=0,messages=[]),sampling={},canonical=None,digest=None)

if __name__=='__main__':unittest.main()
