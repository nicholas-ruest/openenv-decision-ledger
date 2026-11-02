"""Already-seen Native fixture with mocked case admission and synthetic replies."""
import argparse,copy,importlib.util,json,os,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import case_replay as r


class BoundReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jobs=r.binding.gate.jobs_for(dict(task_id='software_repair-ignore-d3',new_seed=2560000))
        cls.args=SimpleNamespace(expected_source='0'*40)
        cls.verdict=dict(jobs=cls.jobs,case_audit_sha256='a'*64)
        cls.gate=patch.object(r.binding.gate,'require_case',return_value=cls.verdict)
        cls.gate.start();cls.addClassCleanup(cls.gate.stop)
        runtime=r.binding._runtime();root=runtime.r.ROOT
        sys.path.insert(0,str(root/'integrations/openenv-arena'))
        spec=importlib.util.spec_from_file_location('case_replay_actual_counter',root/'integrations/openenv-arena/scripts/calibrate.py')
        helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
        cls.counter=helper.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=Path(os.environ['HELPER_TEST_TOKENIZER']),tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
        from repair_env.tasks import make_task
        good=make_task('software_repair-ignore-d3',2560000).reference_source
        cls.traces=[]
        for job in cls.jobs:
            trial=r.binding.materialize(job,cls.args);responses=[]
            for turn in range(2):
                message=dict(role='assistant',content=json.dumps(dict(content=good if turn==0 else '')))
                response=dict(id='synthetic-bound-'+job['attempt_id']+':'+str(turn),usage=dict(prompt_tokens=cls.counter.context(trial.messages),completion_tokens=cls.counter.count(message['content'])),choices=[dict(message=message,finish_reason='stop')])
                responses.append(response);trial.consume(message,'stop')
            cls.traces.append(r.reconstruct(job,responses,cls.counter,cls.args))

    def test_full_phase_replays_original_costs_and_exposure_without_live_authority(self):
        value=r.verify_phase(self.traces,self.counter,self.args)
        self.assertEqual(len(value['rows']),8);self.assertTrue(value['all_assigned_in_denominator'])
        self.assertFalse(value['provider_provenance_attested']);self.assertFalse(value['execution_authorized']);self.assertFalse(value['selection_passed'])
        for row in value['rows']:
            self.assertEqual(row['category'],'full');self.assertEqual(row['semantic_reward'],1)
            self.assertEqual(row['completion_with_observations'],row['generation_tokens']+row['native_observation_tokens'])
            self.assertEqual(row['final_domain_reminder_exposed'],row['job']['arm']=='final_domain_reminder')

    def test_tampered_raw_reconstruction_never_passes(self):
        for field in ['source','case_audit_sha256','requests','record','provider_provenance_attested']:
            t=copy.deepcopy(self.traces[1])
            if field in ('source','case_audit_sha256'):t[field]='wrong'
            elif field=='requests':t[field][1]['max_tokens']-=1
            elif field=='record':t[field]['native_observation_tokens']-=1
            else:t[field]=True
            with self.assertRaises(ValueError):r.verify(t,self.counter,self.args)

    def test_incomplete_reordered_and_reused_reply_phases_refused(self):
        variants=[self.traces[:-1],list(reversed(self.traces))]
        reused=copy.deepcopy(self.traces);reused[1]['responses'][0]['id']=reused[0]['responses'][0]['id'];variants.append(reused)
        for traces in variants:
            with self.assertRaises(ValueError):r.verify_phase(traces,self.counter,self.args)

    def test_unsealed_public_source_refuses_before_trial_runtime(self):
        self.gate.stop()
        try:
            with patch.object(r.binding,'_runtime',side_effect=AssertionError('must not import Native')):
                with self.assertRaisesRegex(ValueError,'unsealed'):r.reconstruct({},[],None,None)
        finally:self.gate.start()

if __name__=='__main__':unittest.main()
