"""Scripted native tests only, no provider or real receipt operations."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import feasibility as f


class NativeTests(unittest.TestCase):
    def test_plan_changes_only_request_generation_limit_within_each_case(self):
        value=f.plan();jobs=value['jobs'];self.assertEqual(len(jobs),4)
        self.assertEqual(len({j['attempt_id'] for j in jobs}),4)
        for a,b in (jobs[:2],jobs[2:]):
            self.assertEqual(a['prompt_sha256'],b['prompt_sha256'])
            self.assertEqual(a['problem_sha256'],b['problem_sha256'])
            x=dict(a['request']);y=dict(b['request']);x.pop('max_tokens');y.pop('max_tokens')
            self.assertEqual(x,y);self.assertEqual({a['max_tokens'],b['max_tokens']},{2048,4000})
        self.assertFalse(value['confirmation']);self.assertFalse(value['promotion'])

    def test_cli_supervision_refuses_missing_audit_before_any_provider_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);inputs=root/'inputs.json';inputs.write_text(json.dumps(f.plan()))
            head=subprocess.check_output(['git','-C',str(f.ROOT),'rev-parse','HEAD'],text=True).strip()
            argv=[sys.executable,str(Path(f.__file__)), '--inputs',str(inputs),
                  '--inputs-sha256',f.protocol.digest(f.plan()),'--receipt',str(root/'missing-receipt'),
                  '--audit',str(root/'missing-audit'),'--tokenizer',str(root/'missing-tokenizer'),
                  '--output',str(root/'out'),'--expected-source',head,'--amendment-sha256','0'*64]
            result=subprocess.run(argv,capture_output=True,text=True,timeout=30)
            self.assertTrue((root/'out.supervision.jsonl').exists(),result.stderr)
            events=[json.loads(x) for x in (root/'out.supervision.jsonl').read_text().splitlines()]
            self.assertEqual(events[-1]['event'],'terminal')
            self.assertTrue(events[-1]['shutdown_verified'])
            self.assertNotEqual(events[-1]['worker_exitcode'],0)
            self.assertFalse((root/'out').exists())

    def run_phase(self, fail=False):
        from repair_env.tasks import make_task
        from decimal import Decimal
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);inputs=root/'inputs.json';inputs.write_text(json.dumps(f.plan()))
            helper=f.load('budget_native_counter',f.ROOT/'scripts/repair-signal-screen.py').helper
            counter=helper.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=Path('/home/ruv/arena-tokenizer.json'),tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
            ledger=root/'fictional.jsonl';ledger.write_text('')
            class FakeBackend:
                credit=Decimal(100)
                frozen={'provider':{'pricing':{'input':0.2,'output':2.5}}}
                calls=0
                def __init__(self,*args):
                    self.counter=counter;self.budget=argparse.Namespace(cap=Decimal(100),ledger=ledger)
                def reserve(self,*args):pass
                def check_reply(self,*args):pass
                def check_message(self,*args):pass
                def call(self,payload,timeout,job):
                    self.calls+=1
                    if fail:raise TimeoutError('fictional failure')
                    content=json.dumps({'content':make_task(job['task_id'],job['seed']).reference_source})
                    return dict(id='scripted-'+job['attempt_id'],usage=dict(prompt_tokens=counter.context(payload['messages']),completion_tokens=counter.count(content)),choices=[dict(message=dict(role='assistant',content=content),finish_reason='stop')])
            args=argparse.Namespace(inputs=inputs,inputs_sha256=f.protocol.digest(f.plan()),receipt=None,audit=None,tokenizer=None,amendment_sha256=None,output=root/'out')
            with patch.object(f,'LiveBackend',FakeBackend):f.execute(time.monotonic()+90,args)
            rows=[json.loads(x) for x in (args.output/'records.jsonl').read_text().splitlines()]
            return rows

    def test_scripted_reference_actions_receive_native_full_credit_under_both_limits(self):
        rows=self.run_phase();self.assertEqual(len(rows),4)
        self.assertTrue(all(r['category']=='full' and r['native_reward']==1 for r in rows))

    def test_provider_failure_keeps_assignment_denominator_and_stops_calls(self):
        rows=self.run_phase(True);self.assertEqual(len(rows),4)
        self.assertEqual(rows[0]['category'],'provider');self.assertIsNone(rows[0]['generation_tokens'])
        self.assertTrue(all(r['category']=='budget' and r['call_id'] is None for r in rows[1:]))


if __name__=='__main__':unittest.main()
