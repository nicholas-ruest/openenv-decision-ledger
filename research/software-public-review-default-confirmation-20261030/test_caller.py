"""Scripted Native trajectories and real CLI refusal, never model results."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from caller import ROOT,load,modules,phase,LiveBackend

class ScriptedBackend:
    scripted=True
    def __init__(self,counter,fail_at=None,truncate=False,early=False,context_overflow=False):
        self.counter=counter;self.fail_at=fail_at;self.truncate=truncate;self.early=early
        self.context_overflow=context_overflow;self.calls=[];self.reserved=[];self.admissions=[]
    def admit(self,bounds,generation,deadline):self.admissions.append((bounds,generation))
    def reserve(self,label,prompt,generation,deadline):self.reserved.append((label,prompt,generation))
    def check_reply(self,response):pass
    def check_message(self,message):pass
    def call(self,payload,timeout,job):
        self.calls.append(payload)
        if len(self.calls)==self.fail_at:raise TimeoutError('fictional unknown-usage second turn')
        from repair_env.tasks import make_task
        first=len(payload['messages'])==2
        reset=json.loads(payload['messages'][1]['content'])
        source=make_task(job['task_id'],job['seed']).reference_source if self.early or not first else reset['source']
        content=json.dumps(dict(content=source,submit=self.early or not first))
        n=payload['max_tokens'] if self.truncate else self.counter.count(content)
        prompt=24576 if self.context_overflow else self.counter.context(payload['messages'])
        return dict(id='scripted-'+str(len(self.calls)),usage=dict(prompt_tokens=prompt,completion_tokens=n),
            choices=[dict(message=dict(role='assistant',content=content),finish_reason='length' if self.truncate else 'stop')])

class NativeFeedbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol,_=modules();cls.bundle=cls.protocol.bundle(0);cls.digest=cls.protocol.digest(cls.bundle)
        helper=load('feedback_native_counter',ROOT/'integrations/openenv-arena/scripts/calibrate.py')
        cls.counter=helper.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=Path('/home/ruv/arena-tokenizer.json'),tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
    def run_phase(self,backend):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'out';rows=phase(self.bundle,self.digest,out,backend,self.counter,time.monotonic()+90)
            summary=json.loads((out/'complete.json').read_text())
            return rows,summary
    def test_exact_first_prompt_and_disjoint_unmaterialized_confirmation(self):
        bundles=[self.protocol.bundle(i) for i in range(4)]
        self.assertEqual([j for b in bundles for j in b['confirmation_jobs']],self.protocol.schedule('confirmation'))
        self.assertEqual(len({j['attempt_id'] for j in self.protocol.schedule('confirmation')}),8)
        arms=bundles[0]['confirmation_groups'][0]['arms']
        self.assertEqual(arms['neutral_review'],arms['public_review'])
        self.assertTrue(bundles[0]['confirmation_observations_materialized'])
        with self.assertRaises(ValueError):self.protocol.capture(self.protocol.schedule('screen')[0])
        with self.assertRaises(ValueError):self.protocol.bundle(True)
    def test_scripted_native_feedback_and_neutral_review_share_first_prompt_and_total_budget(self):
        b=ScriptedBackend(self.counter);rows,summary=self.run_phase(b)
        self.assertEqual(len(b.calls),4);self.assertTrue(all(r['category']=='full' for r in rows))
        self.assertEqual(b.calls[0]['messages'],b.calls[2]['messages'])
        self.assertEqual(b.calls[0]['max_tokens'],6000);self.assertEqual(b.calls[2]['max_tokens'],6000)
        control=json.loads(b.calls[1]['messages'][-1]['content'])
        treatment=json.loads(b.calls[3]['messages'][-1]['content'])
        self.assertEqual(control['reward'],0);self.assertEqual(treatment['reward'],0)
        self.assertEqual(json.loads(control['feedback'])['kind'],'neutral_review')
        self.assertEqual(json.loads(treatment['feedback'])['kind'],'public_field_check')
        feedback=json.loads(treatment['feedback']);self.assertTrue(feedback['public_only']);self.assertFalse(feedback['hidden_access'])
        self.assertEqual(feedback['total'],6)
        self.assertNotIn('chat_template_kwargs',b.calls[0])
        self.assertNotIn('chat_template_kwargs',b.calls[2])
        self.assertNotIn('chat_template_kwargs',b.calls[1])
        self.assertNotIn('chat_template_kwargs',b.calls[3])
        self.assertIn('contract_reminder',json.loads(control['feedback']))
        self.assertIn('contract_reminder',feedback)
        self.assertTrue(all(r['generation_tokens']+r['observation_tokens']<=8192 and r['max_context']<=24576 for r in rows))
        for first,second in [(0,1),(2,3)]:
            first_reply=self.counter.count(json.dumps(dict(content=json.loads(b.calls[first]['messages'][1]['content'])['source'],submit=False)))
            obs=self.counter.count(b.calls[second]['messages'][-1]['content'])
            self.assertEqual(b.calls[second]['max_tokens'],min(8096,8192-first_reply-obs-96))
        self.assertEqual(b.admissions,[([28672]*16,8096)])
        self.assertEqual(len({x[0] for x in b.reserved}),4)
        self.assertTrue(summary['scripted']);self.assertFalse(summary['model_improvement'])
    def test_undeclared_submit_cannot_bypass_required_review(self):
        b=ScriptedBackend(self.counter,early=True);rows,summary=self.run_phase(b)
        self.assertEqual(len(b.calls),4);self.assertEqual(summary['observed_calls'],4)
        self.assertTrue(all(r['category']=='full' and r['turns']==2 for r in rows))
    def test_first_proposal_never_submits_to_the_hidden_grader(self):
        from repair_env.tasks import make_task
        trial=self.protocol.Trial(self.bundle['confirmation_jobs'][1]);core=trial.env._direct._core
        ops=[];original=core.step
        def tracked(action,*args,**kwargs):
            ops.append(action.op);return original(action,*args,**kwargs)
        core.step=tracked
        source=make_task(trial.job['task_id'],trial.job['seed']).reference_source
        first=trial.consume(json.dumps(dict(content=source,submit=True)))
        self.assertEqual(ops,['write']);self.assertFalse(first['done']);self.assertEqual(first['native_reward'],0)
        feedback=json.loads(trial.native[0]['feedback'])
        self.assertTrue(feedback['public_only']);self.assertFalse(feedback['hidden_access'])
        final=trial.consume(json.dumps(dict(content='')))
        self.assertEqual(ops,['write','submit']);self.assertTrue(final['done']);self.assertEqual(final['native_reward'],1)
    def test_first_turn_truncation_cannot_be_revised_or_count_as_partial(self):
        b=ScriptedBackend(self.counter,truncate=True);rows,_=self.run_phase(b)
        self.assertEqual(len(b.calls),2)
        self.assertTrue(all(r['category']=='truncation' and r['generation_tokens']==6000 and r['semantic_reward'] is None for r in rows))
    def test_unknown_second_turn_does_not_hide_behind_known_first_turn_usage(self):
        b=ScriptedBackend(self.counter,fail_at=2);rows,summary=self.run_phase(b)
        self.assertEqual(len(b.calls),2);self.assertEqual(len(rows),2)
        self.assertIsNone(rows[0]['generation_tokens']);self.assertEqual(rows[0]['category'],'provider')
        self.assertEqual(len(rows[0]['reservation_labels']),2)
        self.assertEqual(rows[1]['category'],'budget');self.assertIsNone(rows[1]['call_id'])
    def test_actual_context_overflow_stops_before_another_call(self):
        b=ScriptedBackend(self.counter,context_overflow=True);rows,_=self.run_phase(b)
        self.assertEqual(len(b.calls),1);self.assertEqual(rows[0]['category'],'budget')
        self.assertEqual(rows[1]['category'],'budget');self.assertIsNone(rows[1]['call_id'])
    def test_independent_native_replay_and_usage_tamper_rejection(self):
        from assemble import verify_chunk
        import copy
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'out';b=ScriptedBackend(self.counter)
            rows=phase(self.bundle,self.digest,out,b,self.counter,time.monotonic()+90)
            events=[json.loads(x) for x in (out/'events.jsonl').read_text().splitlines()]
            result=verify_chunk(self.bundle,rows,events,self.counter)
            self.assertEqual(len(result['response_ids']),4);self.assertEqual(len(result['call_ids']),4)
            changed=copy.deepcopy(events)
            next(e for e in changed if e['event']=='response')['response']['usage']['completion_tokens']+=1
            with self.assertRaises(ValueError):verify_chunk(self.bundle,rows,changed,self.counter)
    def test_whole_study_denial_precedes_any_call_or_archive(self):
        from decimal import Decimal
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            ledger=Path(tmp)/'fictional';ledger.write_text('')
            b=object.__new__(LiveBackend);b.budget=SimpleNamespace(cap=Decimal('.1'),ledger=ledger)
            b.credit=Decimal('1');b.frozen={'provider':{'pricing':{'input':1,'output':1}}}
            with self.assertRaises(ValueError):b.admit([28672]*16,8096,time.monotonic()+30)
            self.assertEqual(ledger.read_text(),'')
    def test_actual_cli_missing_audit_fails_under_unchanged_supervisor(self):
        source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'live';inputs=Path(tmp)/'inputs.json';inputs.write_text(json.dumps(self.bundle))
            args=[sys.executable,str(Path(__file__).with_name('caller.py')),'--execute','--expected-source',source,'--inputs',str(inputs),'--inputs-sha256',self.digest,'--receipt',str(Path(tmp)/'receipt'),'--reconciliation',str(Path(tmp)/'missing-audit'),'--tokenizer','/home/ruv/arena-tokenizer.json','--output',str(out),'--amendment-sha256','0'*64,'--screen-gate',str(Path(tmp)/'missing-screen-gate'),'--screen-gate-sha256','0'*64]
            subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=20)
            self.assertFalse(out.exists())
            supervision=[json.loads(x) for x in out.with_suffix('.supervision.jsonl').read_text().splitlines()]
            self.assertEqual(supervision[-1]['status'],'worker_failed');self.assertTrue(supervision[-1]['shutdown_verified'])

if __name__=='__main__':unittest.main()
