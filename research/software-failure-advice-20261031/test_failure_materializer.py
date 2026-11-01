import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import failure_materializer as m
import failure_protocol as p


class MaterializerTests(unittest.TestCase):
    def test_unsealed_screen_and_confirmation_refuse_before_private_reads_or_native(self):
        with patch.object(m,'sha',side_effect=AssertionError('no reads')),patch.object(m,'construct_existing',side_effect=AssertionError('no Native')):
            for job in p.jobs('screen')+p.jobs('confirmation'):
                with self.assertRaises(ValueError):m.materialize(job,'unused','a'*64)
        with patch.dict('os.environ',CASE_AUDIT_SHA256='a'*64):
            with self.assertRaises(ValueError):m.materialize(p.jobs('screen')[0],'unused','a'*64)
        with patch.object(m,'CASE_AUDIT_SHA256','a'*64):
            with self.assertRaises(ValueError):m.materialize(p.jobs('screen')[0],'unused','b'*64)
    def test_factory_matches_qualified_native_prompt_on_already_used_case(self):
        for job in p.jobs('qualification')[:2]:
            baseline=p.QualificationTrial(job);candidate=m.construct_existing(job)
            self.assertEqual(baseline.messages,candidate.messages)
            text=json.dumps(dict(content=json.loads(candidate.messages[1]['content'])['source']))
            self.assertEqual(baseline.consume(text,finish_reason='stop'),candidate.consume(text,finish_reason='stop'))
            self.assertEqual(baseline.messages,candidate.messages)
    def test_inventory_regeneration_rejects_overlap_and_changed_digest_on_used_cases(self):
        from repair_env.tasks import make_task
        from repair_env.direct_environment import DirectRepairEnvironment
        old=make_task(p.TASK,3080000);new=make_task(p.TASK,3100000)
        past={p.digest(c.args) for c in old.public+old.hidden};current={p.digest(c.args) for c in new.public+new.hidden}
        obs=DirectRepairEnvironment().reset(task_id=p.TASK,seed=3100000)
        value=dict(task_id=p.TASK,new_seed=3100000,prior_task_seed_pairs=[[p.TASK,3080000]],prior_case_count=1,prior_input_count=len(past),new_input_count=len(current),prior_input_set_sha256=p.digest(sorted(past)),new_input_set_sha256=p.digest(sorted(current)),new_source_examples_sha256=p.digest(dict(source=obs.source,examples=obs.examples)))
        self.assertTrue(m.verify_inventory(value,dict(task_id=p.TASK,seed=3100000))['verified'])
        for field in ['prior_case_count','new_input_set_sha256','new_source_examples_sha256']:
            bad=copy.deepcopy(value);bad[field]=0
            with self.subTest(field=field),self.assertRaises(ValueError):m.verify_inventory(bad,dict(task_id=p.TASK,seed=3100000))
        bad=copy.deepcopy(value);bad['prior_task_seed_pairs']=[[p.TASK,3100000]]
        with self.assertRaises(ValueError):m.verify_inventory(bad,dict(task_id=p.TASK,seed=3100000))


if __name__=='__main__':unittest.main()
