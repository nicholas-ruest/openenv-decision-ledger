import argparse
import ast
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch
import order_diagnostic as d
import revision_environment as r
from repair_env.direct_environment import DirectRepairEnvironment,DirectRepairAction
from repair_env.tasks import make_task,SOURCE_PATH


class OrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.task=make_task('software_repair-ignore-d3',2560000)
        cls.native=DirectRepairEnvironment().reset(seed=2560000,task_id=cls.task.task_id).model_dump()
        cls.good=cls.task.reference_source
        cls.order_bug="def classify_ignore(lines, entries):\n    result = {}\n    seen = False\n    for entry in entries:\n        result[entry['path']] = seen\n        seen = True\n    return result\n"
        cls.constant_wrong="def classify_ignore(lines, entries):\n    result = {}\n    for entry in entries:\n        result[entry['path']] = False\n    return result\n"

    def test_actual_native_reference_is_order_invariant_and_inputs_unchanged(self):
        before=copy.deepcopy(self.native)
        value=d.diagnose(self.native,self.good)
        self.assertEqual(value['kind'],'public_entry_order_relation');self.assertEqual(value['program_evaluations'],144)
        self.assertEqual(value['order_sensitive_examples'],0);self.assertIsNone(value['first_counterexample'])
        self.assertFalse(value['semantic_correctness_established']);self.assertEqual(self.native,before)

    def test_real_bounded_interpreter_detects_order_bug_without_expected_answers(self):
        a=d.diagnose(self.native,self.order_bug)
        self.assertGreater(a['order_sensitive_examples'],0)
        self.assertEqual(sorted(a['first_counterexample']['zero_based_entry_order']),list(range(4)))
        changed=copy.deepcopy(self.native);examples=ast.literal_eval(changed['examples'])
        examples=[(e[0],{'PRIVATE_EXPECTED_CANARY':'unused'}) for e in examples]
        changed['examples']=repr(examples)
        b=d.diagnose(changed,self.order_bug);self.assertEqual(a,b)
        self.assertNotIn('PRIVATE_EXPECTED_CANARY',d.canonical(b))

    def test_wrong_constant_answer_is_not_promoted_by_consistency(self):
        value=d.diagnose(self.native,self.constant_wrong)
        self.assertEqual(value['order_sensitive_examples'],0);self.assertFalse(value['semantic_correctness_established'])
        native=DirectRepairEnvironment();native.reset(seed=2560000,task_id=self.task.task_id)
        self.assertLess(native.step(DirectRepairAction(content=self.constant_wrong)).reward,1)

    def test_compile_and_runtime_failures_are_not_semantic_results(self):
        for code,reason in [('invalid python','compile_rejected'),('def classify_ignore(lines, entries): return 1 // 0','runtime_rejected')]:
            result=d.diagnose(self.native,code)
            self.assertEqual(result,dict(kind='program_unavailable',reason=reason,public_only=True))
        with patch.object(d.Program,'run',side_effect=OSError('synthetic Native infrastructure fault')):
            with self.assertRaises(OSError):d.diagnose(self.native,self.good)

    def test_two_arms_have_identical_proposals_native_rewards_and_actions(self):
        observations=[];envs=[]
        for arm in d.ARMS:
            env=r.RevisionEnvironment(arm=arm);envs.append(env)
            observations.append(env.reset(seed=2560000,task_id=self.task.task_id).model_dump())
        self.assertEqual(*observations)
        native=DirectRepairEnvironment();native.reset(seed=2560000,task_id=self.task.task_id)
        expected=native.step(DirectRepairAction(content=self.good))
        for env in envs:
            first=env.step(DirectRepairAction(content=self.good));self.assertFalse(first.done);self.assertEqual(first.reward,0)
            final=env.step(DirectRepairAction(content=''));self.assertTrue(final.done);self.assertEqual(final.reward,expected.reward)
            self.assertEqual(env._direct._files[SOURCE_PATH],self.good)
            self.assertEqual(env.step(DirectRepairAction(content=self.constant_wrong)),final)
        self.assertEqual(envs[0].state.step_count,2)

    def test_only_computed_counterexample_exposure_differs_and_costs_are_bounded(self):
        with patch.object(d,'diagnose',wraps=d.diagnose) as observed:
            a=d.review(self.native,self.order_bug,'relation_only');b=d.review(self.native,self.order_bug,'computed_relation')
            self.assertEqual(observed.call_count,2)
        self.assertEqual(a['relation'],b['relation']);self.assertEqual(a['instruction'],b['instruction'])
        self.assertEqual(a['diagnostic']['kind'],'computed_result_withheld')
        self.assertGreater(b['diagnostic']['order_sensitive_examples'],0)
        self.assertNotIn('actual',d.canonical(b));self.assertNotIn('expected',d.canonical(b))
        sys.path.insert(0,str(d.ROOT/'integrations/openenv-arena'))
        spec=importlib.util.spec_from_file_location('relation_counter',d.ROOT/'integrations/openenv-arena/scripts/calibrate.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        counter=module.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=Path(os.environ['HELPER_TEST_TOKENIZER']),tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
        for arm in d.ARMS:
            env=r.RevisionEnvironment(arm=arm);env.reset(seed=2560000,task_id=self.task.task_id)
            obs=env.step(DirectRepairAction(content=self.order_bug));tokens=counter.count(d.canonical(obs.model_dump()))
            self.assertGreater(tokens,0);self.assertGreater(8192-6000-tokens-96,0)
            terminal=env.step(DirectRepairAction(content=self.good))
            self.assertLessEqual(counter.count(d.canonical(terminal.model_dump())),96)
        self.assertFalse(r.plan()['live_execution_ready'])

    def test_review_does_not_read_hidden_grades_or_observation_metadata(self):
        changed=copy.deepcopy(self.native);changed['metadata']={'PRIVATE_HIDDEN_CANARY':'must stay private'}
        self.assertEqual(d.diagnose(changed,self.order_bug),d.diagnose(self.native,self.order_bug))
        for arm in d.ARMS:
            env=r.RevisionEnvironment(arm=arm);env.reset(seed=2560000,task_id=self.task.task_id)
            with patch('repair_env.environment.check',side_effect=AssertionError('no final grade during public review')):
                observation=env.step(DirectRepairAction(content=self.order_bug))
            self.assertFalse(observation.done);self.assertNotIn('PRIVATE_HIDDEN_CANARY',observation.feedback)

    def test_unavailable_program_diagnostic_is_common_to_both_arms(self):
        for code in ('invalid python','def classify_ignore(lines, entries): return 1 // 0'):
            a=d.review(self.native,code,d.ARMS[0]);b=d.review(self.native,code,d.ARMS[1])
            self.assertEqual(a,b);self.assertEqual(a['diagnostic']['kind'],'program_unavailable')

    def test_visible_scope_and_future_cases_stay_closed(self):
        for seed in (3220000,3230000,None):
            with self.assertRaises(ValueError):r.RevisionEnvironment(arm=d.ARMS[0]).reset(seed=seed,task_id=self.task.task_id)
        with self.assertRaises(ValueError):r.materialize()
        with self.assertRaises(ValueError):d.review(self.native,self.good,'automatic')
        with self.assertRaises(ValueError):d.diagnose(dict(task_id='software_repair-kv-d2',examples='[]'),self.good)
        with self.assertRaises(ValueError):d.diagnose(dict(task_id=self.task.task_id,examples='[]'),self.good)
        # The diagnostic can only see a visible observation and program: its
        # module imports no task generator, semantic grader or reference source.
        tree=ast.parse(Path(d.__file__).read_text())
        names={x.id for x in ast.walk(tree) if isinstance(x,ast.Name)}
        self.assertTrue({'make_task','check','reference_source','hidden'}.isdisjoint(names))


if __name__=='__main__':unittest.main()
