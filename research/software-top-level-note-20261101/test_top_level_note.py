import argparse
import copy
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import top_level_note as p


class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p.Binding(p.job('baseline'))

    def trials(self):return [p.QualificationTrial(p.job(a)) for a in p.ARMS]

    def test_only_fixed_syntax_note_changes_with_identical_original_schema_problem(self):
        a,b=self.trials()
        self.assertEqual(a.messages[0],b.messages[0])
        x,y=[json.loads(t.messages[1]['content']) for t in (a,b)]
        self.assertEqual(y.pop('prompt'),x.pop('prompt')+p.NOTE);self.assertEqual(x,y)
        self.assertEqual(a.binding.problem_sha256,b.binding.problem_sha256)
        baseline=p.original.QualificationTrial(p.original.qualification_job('baseline'))
        self.assertEqual(a.messages,baseline.messages)
        self.assertNotIn('Repair focus:',b.messages[1]['content'])

    def test_actual_reference_repairs_grade_identically_without_code_rewriting(self):
        from repair_env.tasks import make_task,SOURCE_PATH
        code=make_task(p.original.TASK,p.original.QUALIFICATION_SEED).reference_source
        reply=json.dumps(dict(content=code))
        for t in self.trials():
            r=t.consume(reply,finish_reason='stop')
            self.assertEqual(r['category'],'full');self.assertEqual(r['native_reward'],1)
            self.assertEqual(r['failure_origin'],'native_semantic_outcome')
            self.assertEqual(t.binding.env._files[SOURCE_PATH],code)
            self.assertEqual(t.messages[2]['content'],reply)
            self.assertEqual(r['controller_actions'],[])
            with self.assertRaises(ValueError):t.consume(reply,finish_reason='stop')

    def test_real_nested_function_rejection_remains_zero_native_reward(self):
        # Synthetic negative control, not a sampled model reply or new task.
        code='def classify_ignore(path, rules):\n    def helper(x):\n        return x\n    return helper(False)\n'
        for t in self.trials():
            r=t.consume(json.dumps(dict(content=code)),finish_reason='stop')
            self.assertEqual(r['category'],'execution');self.assertTrue(r['compile_rejected'])
            self.assertEqual(r['native_reward'],0);self.assertIsNone(r['semantic_reward'])
            self.assertEqual(r['failure_origin'],'model_program_rejection')

    def test_real_program_runtime_error_is_distinct_from_native_step_exception(self):
        a,b=self.trials()
        r=a.consume('{"content":"def classify_ignore(path, rules): return 1 // 0"}',finish_reason='stop')
        self.assertEqual(r['failure_origin'],'model_program_runtime_error')
        self.assertEqual(r['native_reward'],0)
        with patch.object(b.binding,'step',side_effect=RuntimeError('synthetic Native failure')):
            r=b.consume('{"content":""}',finish_reason='stop')
        self.assertEqual(r['category'],'execution');self.assertEqual(r['failure_origin'],'native_execution_unverified')
        self.assertIsNone(b.native);self.assertIsNone(r['native_reward'])

    def test_format_length_and_provider_failures_remain_terminal_without_replacement(self):
        for finish,text,origin in [('stop','invalid json','model_output_format'),
                                   ('length','unfinished','model_output_truncation'),
                                   ('error','{}','provider_failure')]:
            t=p.QualificationTrial(p.job('top_level_only'));r=t.consume(text,finish_reason=finish)
            self.assertEqual(r['failure_origin'],origin);self.assertIsNone(t.native)
            with self.assertRaises(ValueError):t.consume('{}',finish_reason='stop')

    def test_future_plan_cannot_reset_new_cases_or_enable_live_execution(self):
        with patch.object(p,'QualificationTrial',side_effect=AssertionError('no capture')):
            plan=p.plan()
        self.assertFalse(plan['live_execution_ready']);self.assertFalse(plan['live_continuation_policy_frozen'])
        self.assertEqual(plan['limits']['first_generation_limit'],6000)
        for arm in p.ARMS:
            j=p.job(arm);j['seed']=3200000
            with self.assertRaises(ValueError):p.Binding(j)
        with self.assertRaises(ValueError):p.materialize(p.job('baseline'))
        with self.assertRaises(ValueError):p.outcome_origin(dict(category='full'),None)

    def test_actual_observation_counts_fit_original_pinned_tokenizer_limits(self):
        from repair_env.tasks import make_task
        sys.path.insert(0,str(p.ROOT/'integrations/openenv-arena'))
        module=p.original.load('top_level_counter','integrations/openenv-arena/scripts/calibrate.py')
        counter=module.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=Path(os.environ['HELPER_TEST_TOKENIZER']),
            tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
        reply=json.dumps(dict(content=make_task(p.original.TASK,p.original.QUALIFICATION_SEED).reference_source))
        for t in self.trials():
            self.assertLessEqual(counter.context(t.messages)+6000+96,24576)
            r=t.consume(reply,finish_reason='stop')
            observed=sum(counter.count(p.original.canonical(x)) for x in r['new_observations'])
            self.assertGreater(observed,0);self.assertLessEqual(observed,96)
            self.assertLessEqual(counter.count(reply)+observed,8192)


if __name__=='__main__':unittest.main()
