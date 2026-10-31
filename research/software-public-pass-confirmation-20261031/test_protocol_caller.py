"""Scripted existing-case Native controls; no paid backend construction."""
import argparse
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import caller
protocol, _ = caller.modules()


class Backend:
    scripted = True
    def __init__(self, counter, fail_at=None, truncate=False):
        self.counter=counter; self.fail_at=fail_at; self.truncate=truncate
        self.calls=[]; self.reservations=[]
    def admit(self, *args): pass
    def reserve(self, label, *args): self.reservations.append(label)
    def check_reply(self, response): pass
    def check_message(self, message): pass
    def call(self, payload, timeout, job):
        from repair_env.tasks import make_task
        self.calls.append(payload)
        if len(self.calls)==self.fail_at: raise TimeoutError('scripted unknown usage')
        text=json.dumps(dict(content=make_task(job['task_id'],job['seed']).reference_source))
        return dict(id='trusted-'+job['attempt_id']+'-'+str(len(payload['messages'])),
            usage=dict(prompt_tokens=self.counter.context(payload['messages']),completion_tokens=payload['max_tokens'] if self.truncate else self.counter.count(text)),
            choices=[dict(message=dict(role='assistant',content=text),finish_reason='length' if self.truncate else 'stop')])


class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=os.environ['FINALIZATION_TEST_TOKENIZER']
        helper=caller.load('policy_test_counter',caller.ROOT/'integrations/openenv-arena/scripts/calibrate.py')
        cls.counter=helper.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=Path(path),
            tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))

    def test_plan_and_confirmation_metadata_do_not_materialize_new_cases(self):
        with patch.object(protocol,'Trial',side_effect=AssertionError('must not instantiate')):
            self.assertEqual(len(protocol.plan()['confirmation_jobs']),8)
            self.assertEqual(protocol.SEEDS,dict(screen=3120000,confirmation=3130000))
            with self.assertRaises(ValueError): protocol.capture(protocol.schedule('confirmation')[0])

    def test_same_prompt_three_actual_replies_and_both_controller_observations_counted(self):
        # Only trusted controls use the already materialized qualification seed.
        # There is no production seed override or paid-admission bypass.
        with patch.dict(protocol.SEEDS,confirmation=3100000),patch.object(protocol,"GATE_VERIFIED",True):
            bundle=protocol.bundle(0)
            captures=[protocol.capture(j) for j in bundle['confirmation_jobs']]
            self.assertEqual(captures[0]['messages'],captures[1]['messages'])
            self.assertEqual(protocol.sampling_for(bundle['confirmation_jobs'][0],0),protocol.sampling_for(bundle['confirmation_jobs'][1],0))
            backend=Backend(self.counter)
            with tempfile.TemporaryDirectory() as t:
                out=Path(t)/'live';rows=caller.phase(bundle,protocol.digest(bundle),out,backend,self.counter,time.monotonic()+90)
                self.assertEqual(len(backend.calls),3)
                self.assertEqual(len(backend.reservations),3)
                self.assertEqual([r['category'] for r in rows],['full','full'])
                self.assertEqual([r['turns'] for r in rows],[2,1])
                self.assertEqual([len(r['controller_actions']) for r in rows],[0,1])
                events=[json.loads(x) for x in (out/'events.jsonl').read_text().splitlines()]
                self.assertEqual(sum(e['event']=='controller_actions' for e in events),1)
                job=bundle['confirmation_jobs'][1];trial=protocol.Trial(job)
                reply=next(e['response'] for e in events if e['event']=='response' and e['attempt_id']==job['attempt_id'])
                value=trial.consume(reply['choices'][0]['message']['content'])
                self.assertEqual(len(value['new_observations']),2)
                expected=sum(self.counter.count(protocol.canonical(x)) for x in value['new_observations'])
                self.assertEqual(rows[1]['observation_tokens'],expected)
                replay=caller.load('exact_policy_replay',Path(__file__).with_name('replay.py'))
                self.assertEqual(Path(replay.__file__).resolve(),Path(__file__).with_name('replay.py').resolve())
                verify_chunk=replay.verify_chunk
                proof=verify_chunk(bundle,rows,events,self.counter)
                self.assertEqual(len(proof['call_ids']),3)
                import copy
                altered=copy.deepcopy(rows);altered[1]['observation_tokens']=self.counter.count(protocol.canonical(value['new_observations'][-1]))
                with self.assertRaisesRegex(ValueError,'actual cost changed'):verify_chunk(bundle,altered,events,self.counter)
                altered_events=copy.deepcopy(events)
                next(e for e in altered_events if e['event']=='controller_actions')['actions'][0]['authored_by']='model'
                with self.assertRaisesRegex(ValueError,'controller provenance changed'):verify_chunk(bundle,rows,altered_events,self.counter)
                self.assertGreater(expected,self.counter.count(protocol.canonical(value['new_observations'][-1])))
                with self.assertRaises(ValueError): caller.phase(bundle,protocol.digest(bundle),out,backend,self.counter,time.monotonic()+90)

    def test_unknown_usage_stops_without_controller_or_next_attempt_call(self):
        with patch.dict(protocol.SEEDS,confirmation=3100000),patch.object(protocol,"GATE_VERIFIED",True),tempfile.TemporaryDirectory() as t:
            b=protocol.bundle(0);backend=Backend(self.counter,fail_at=2)
            rows=caller.phase(b,protocol.digest(b),Path(t)/'live',backend,self.counter,time.monotonic()+90)
            self.assertEqual(len(backend.calls),2);self.assertEqual(len(backend.reservations),2)
            self.assertIsNone(rows[0]['generation_tokens'])
            self.assertEqual(rows[0]['category'],'provider')
            self.assertEqual(rows[1]['category'],'budget')
            self.assertEqual(rows[1]['call_ids'],[])

    def test_truncation_does_not_trigger_retention(self):
        with patch.dict(protocol.SEEDS,confirmation=3100000),patch.object(protocol,"GATE_VERIFIED",True),tempfile.TemporaryDirectory() as t:
            b=protocol.bundle(0);backend=Backend(self.counter,truncate=True)
            rows=caller.phase(b,protocol.digest(b),Path(t)/'live',backend,self.counter,time.monotonic()+90)
            self.assertEqual(len(backend.calls),2)
            self.assertTrue(all(r['category']=='truncation' and not r['controller_actions'] for r in rows))

    def test_case_lease_remains_unsealed(self):
        with patch.object(caller,'LIVE_CASE_AUDIT_SHA256',None):
            with self.assertRaisesRegex(ValueError,'unsealed'):
                caller.require_case_lease(Path('/nonexistent'),'0'*64)

    def test_wrong_sealed_case_digest_refused(self):
        with patch.object(caller,'LIVE_CASE_AUDIT_SHA256','a'*64):
            with self.assertRaisesRegex(ValueError,'sealed case audit differs'):
                caller.require_case_lease(Path('/nonexistent'),'0'*64)


if __name__=='__main__': unittest.main()
