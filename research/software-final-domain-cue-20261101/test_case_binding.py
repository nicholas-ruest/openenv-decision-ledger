"""Actual Native binding on already-seen fixture; case gate mocked explicitly."""
import copy,json,sys,unittest
from types import SimpleNamespace
from unittest.mock import patch
import case_binding as b


class BindingTests(unittest.TestCase):
    def jobs(self):
        return b.gate.jobs_for(dict(task_id='software_repair-ignore-d3',new_seed=2560000))

    def verdict(self):return dict(jobs=self.jobs(),case_audit_sha256='a'*64)

    def trial(self,job):
        with patch.object(b.gate,'require_case',return_value=self.verdict()):
            return b.materialize(job,SimpleNamespace())

    def test_unsealed_refuses_before_runtime_or_arguments(self):
        with patch.object(b,'_runtime',side_effect=AssertionError('Native import')):
            with self.assertRaisesRegex(ValueError,'unsealed'):b.materialize({},None)

    def test_changed_job_and_bool_sample_refused_before_native(self):
        jobs=self.jobs();job=copy.deepcopy(jobs[2]);job['sample']=True
        for bad in [dict(jobs[0],seed=9999999),dict(jobs[0],arm='computed_relation'),job]:
            with patch.object(b.gate,'require_case',return_value=self.verdict()),patch.object(b,'_runtime',side_effect=AssertionError('Native import')):
                with self.assertRaisesRegex(ValueError,'exact original'):b.materialize(bad,None)

    def test_existing_fixture_prompts_identical_only_late_cue_differs(self):
        trials=[self.trial(j) for j in self.jobs()[:2]]
        self.assertEqual(trials[0].messages,trials[1].messages)
        from repair_env.tasks import make_task
        source=make_task('software_repair-ignore-d3',2560000).reference_source
        results=[t.consume({'role':'assistant','content':json.dumps({'content':source})},'stop') for t in trials]
        feedback=[json.loads(r['new_observations'][0]['feedback']) for r in results]
        self.assertIn('final_output_domain_reminder',feedback[1]);feedback[1].pop('final_output_domain_reminder')
        self.assertEqual(*feedback)
        for t in trials:
            result=t.consume({'role':'assistant','content':'{"content":""}'},'stop')
            self.assertEqual(result['category'],'full');self.assertEqual(result['semantic_reward'],1)
            self.assertEqual(t.case_audit_sha256,'a'*64)

    def test_environment_cannot_reset_to_another_case(self):
        job=self.jobs()[0];trial=self.trial(job)
        with self.assertRaisesRegex(ValueError,'immutable task and seed'):trial.env.reset(seed=job['seed']+1,task_id=job['task_id'])
        job['seed']+=1
        self.assertEqual(trial.job['seed'],2560000)

    def test_binding_is_in_original_method_inventory(self):
        self.assertIn('research/software-final-domain-cue-20261101/case_binding.py',b.gate.FILES)
        self.assertIsNone(b.gate.CASE_AUDIT_SHA256);self.assertIsNone(b.gate.LATEST_CLOSED_AUDIT_SHA256)

if __name__=='__main__':unittest.main()
