"""Lease rejection and already-used-case Native controls. No future case capture."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import matched_protocol as p
import screen_materializer as m


class MaterializerTests(unittest.TestCase):
    def test_default_source_and_confirmation_refuse_before_native_construction(self):
        with patch.object(m,'construct_existing_trial',side_effect=AssertionError('no capture')):
            for job in p.jobs('screen')+p.jobs('confirmation'):
                with self.assertRaises(ValueError):p.materialize(job)

    def test_cli_environment_and_wrong_hash_cannot_replace_source_lease(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'fake.json';path.write_text('{}')
            with patch.dict('os.environ',LIVE_CASE_AUDIT_SHA256=m.sha(path)):
                with self.assertRaises(ValueError):m.verify_live_case(p.jobs('screen')[0],path,m.sha(path))
            with patch('finite_caller.LIVE_CASE_AUDIT_SHA256','a'*64):
                with self.assertRaises(ValueError):m.verify_live_case(p.jobs('screen')[0],path,m.sha(path))

    def test_unsealed_materializer_does_not_read_private_paths(self):
        with patch.object(m,'sha',side_effect=AssertionError('no private reads')):
            with self.assertRaises(ValueError):m.verify_live_case(p.jobs('screen')[0],'/unused','a'*64)

    def test_native_factory_preserves_original_matched_prompt_and_controller_behavior(self):
        from repair_env.tasks import make_task
        job=p.jobs('qualification')[1]
        old=p.QualificationTrial(job);new=m.construct_existing_trial(job)
        self.assertEqual(old.messages,new.trial.messages)
        code=make_task(p.TASK,3100000).reference_source.replace('return table[len(tokens)][len(word)]','return False')
        first=new.consume_model(json.dumps(dict(content=code)),finish_reason='stop')
        self.assertFalse(first['done']);self.assertEqual(len(first['controller_actions']),1)
        final=new.consume_model(json.dumps(dict(content='')),finish_reason='stop')
        self.assertEqual(final['category'],'full')

    def test_independent_case_inventory_regeneration_on_existing_cases(self):
        from repair_env.tasks import make_task
        from repair_env.direct_environment import DirectRepairEnvironment
        job=p.jobs('qualification')[0];pairs=[[p.TASK,3080000]]
        t=make_task(p.TASK,3080000);past={p.digest(c.args) for c in t.public+t.hidden}
        t=make_task(p.TASK,3100000);current={p.digest(c.args) for c in t.public+t.hidden}
        obs=DirectRepairEnvironment().reset(task_id=p.TASK,seed=3100000)
        value=dict(task_id=p.TASK,new_seed=3100000,prior_task_seed_pairs=pairs,prior_case_count=1,
            prior_input_count=len(past),new_input_count=len(current),prior_input_set_sha256=p.digest(sorted(past)),
            new_input_set_sha256=p.digest(sorted(current)),new_source_examples_sha256=p.digest(dict(source=obs.source,examples=obs.examples)))
        self.assertTrue(m.verify_case_contents(value,job)['verified'])
        for field in ['prior_case_count','new_input_set_sha256','new_source_examples_sha256']:
            bad=copy.deepcopy(value);bad[field]=0
            with self.subTest(field=field),self.assertRaises(ValueError):m.verify_case_contents(bad,job)
        bad=copy.deepcopy(value);bad['prior_task_seed_pairs']=[[p.TASK,3100000]]
        with self.assertRaises(ValueError):m.verify_case_contents(bad,job)


if __name__=='__main__':unittest.main()
