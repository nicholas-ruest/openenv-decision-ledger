"""Full assigned-phase controls; actual pinned fitness, no live evidence."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

import finite_caller as caller
import test_finite_caller as fixture
from assemble_phase import assemble


def score(report):
    module=Path(__file__).with_name('assess_qualification.mjs').as_uri()
    js="import {readFileSync} from 'node:fs';import {assess} from "+json.dumps(module)+";console.log(JSON.stringify(assess(JSON.parse(readFileSync(0,'utf8')))));"
    r=subprocess.run(['node','--input-type=module','-e',js],input=json.dumps(report),text=True,capture_output=True,check=True)
    return json.loads(r.stdout)


class PhaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.CallerTests.setUpClass();cls.counter=fixture.CallerTests.counter
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
        cls.paths=[]
        for i in range(4):
            path=cls.root/f'chunk{i}';cls.paths.append(path)
            caller.qualification_chunk(i,fixture.Backend(cls.counter),cls.counter,path,time.monotonic()+120)
        cls.report=assemble(cls.paths,cls.counter)
        cls.scored=score(cls.report)

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_complete_phase_uses_real_fitness_and_separates_controller_outcomes(self):
        self.assertTrue(self.report['complete']);self.assertEqual(self.report['independently_replayed'],8)
        self.assertEqual(self.report['actual_scripted_calls'],16)
        self.assertEqual(self.scored['actual_module'],'fitness.mjs:scoreCell')
        self.assertEqual(self.scored['metaharness_source'],'b8c3d38de41203faf633ef6dceb8452a4727b0ea')
        treatment=self.scored['groups'][1]
        self.assertEqual(treatment['controller_assisted_full'],4)
        self.assertEqual(treatment['model_response_only_full'],0)
        self.assertFalse(self.scored['selection_passed']);self.assertFalse(self.scored['live_evidence'])

    def test_missing_last_chunk_keeps_all_original_assignments(self):
        report=assemble(self.paths[:3]+[self.root/'missing'],self.counter);result=score(report)
        self.assertEqual(report['assigned'],8);self.assertEqual(report['recorded'],6)
        self.assertEqual(report['unexecuted'],2);self.assertFalse(report['complete'])
        self.assertTrue(all(g['assigned']==4 and g['metaharness'] is None for g in result['groups']))

    def test_unknown_usage_is_retained_without_fictional_fitness_cost(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'chunk0'
            caller.qualification_chunk(0,fixture.Backend(self.counter,fail_at=2),self.counter,path,time.monotonic()+60)
            paths=[path]+[root/f'missing{i}' for i in range(1,4)]
            report=assemble(paths,self.counter);result=score(report)
            self.assertIsNone(report['rows'][0]['generation_tokens']);self.assertTrue(report['rows'][0]['unknown_usage'])
            self.assertEqual(report['actual_scripted_calls'],2);self.assertEqual(report['known_scripted_replies'],1)
            self.assertEqual(report['unexecuted'],7);self.assertIsNone(result['actual_module'])
            rows=[json.loads(l) for l in (path/'records.jsonl').read_text().splitlines()]
            rows[0]['unknown_usage']=False;rows[0]['generation_tokens']=0
            (path/'records.jsonl').write_text('\n'.join(json.dumps(r) for r in rows))
            with self.assertRaises(ValueError):assemble(paths,self.counter)

    def test_record_and_identity_tampering_are_rejected(self):
        for kind in ('identity','receipt_cost'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);paths=[]
                for i,path in enumerate(self.paths):
                    target=root/f'chunk{i}';shutil.copytree(path,target);paths.append(target)
                rows=[json.loads(l) for l in (paths[0]/'records.jsonl').read_text().splitlines()]
                if kind=='identity':rows[1]['job']=rows[0]['job']
                else:rows[1]['controller_observation_tokens']=0
                (paths[0]/'records.jsonl').write_text('\n'.join(json.dumps(r) for r in rows))
                with self.assertRaises(ValueError):assemble(paths,self.counter)

    def test_scripted_report_cannot_be_relabelled_as_live_or_pool_future_cases(self):
        for mutate in ('live','future'):
            bad=copy.deepcopy(self.report)
            if mutate=='live':bad['scripted']=False;bad['live_evidence']=True
            else:bad['rows'][0]['job']['seed']=3140000
            with self.subTest(mutate=mutate),self.assertRaises(subprocess.CalledProcessError):score(bad)

    def test_json_key_order_does_not_change_assignment_identity(self):
        changed=copy.deepcopy(self.report)
        changed['assigned_jobs']=[dict(reversed(list(j.items()))) for j in changed['assigned_jobs']]
        self.assertEqual(score(changed),self.scored)

    def test_assessment_rejects_hidden_receipt_cost_or_over_budget_semantic_grade(self):
        for kind in ('receipt_cost','over_budget','native_reward'):
            bad=copy.deepcopy(self.report);row=next(r for r in bad['rows'] if r['job']['arm']=='preserve_declared_helpers')
            if kind=='receipt_cost':row['controller_observation_tokens']=0
            elif kind=='over_budget':
                row['generation_tokens']=8193
                row['completion_with_observations']=8193+row['native_observation_tokens']+row['controller_observation_tokens']
            else:row['terminal_reward_observed']=0
            with self.subTest(kind=kind),self.assertRaises(subprocess.CalledProcessError):score(bad)


if __name__=='__main__':unittest.main()
