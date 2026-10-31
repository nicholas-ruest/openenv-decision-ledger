"""Finite scripted Native calls only; no provider, credit or ledger fixtures."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import caller
from replay import verify_chunk


class ScriptedBackend:
    scripted = True
    def __init__(self, counter, fail_at=None, truncate=False):
        self.counter=counter; self.fail_at=fail_at; self.truncate=truncate
        self.calls=[]; self.reserved=[]; self.admitted=[]
    def admit(self, bounds, generation, deadline): self.admitted.append((bounds,generation))
    def reserve(self, label, prompt, generation, deadline): self.reserved.append(label)
    def check_reply(self, reply): pass
    def check_message(self, message): pass
    def call(self, payload, timeout, job):
        from repair_env.tasks import make_task
        self.calls.append(payload)
        if len(self.calls)==self.fail_at: raise TimeoutError('scripted unknown usage')
        task=make_task(job['task_id'],job['seed'])
        source=task.initial_source if len(payload['messages'])==2 else task.reference_source
        content=json.dumps(dict(content=source))
        return dict(id='scripted-'+job['attempt_id']+'-'+str(len(payload['messages'])),
            usage=dict(prompt_tokens=self.counter.context(payload['messages']),
                       completion_tokens=payload['max_tokens'] if self.truncate else self.counter.count(content)),
            choices=[dict(message=dict(role='assistant',content=content),
                          finish_reason='length' if self.truncate else 'stop')])


class FiniteCallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=os.environ.get('ACTION_EXAMPLE_TEST_TOKENIZER')
        if not path: raise unittest.SkipTest('explicit pinned public tokenizer required')
        cls.protocol,_=caller.modules()
        cls.bundle=cls.protocol.bundle(0)
        helper=caller.load('finite_counter',caller.ROOT/'integrations/openenv-arena/scripts/calibrate.py')
        cls.counter=helper.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=Path(path),
            tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))

    def test_finite_native_phase_replays_under_same_budgets_and_fresh_archive_rule(self):
        b=ScriptedBackend(self.counter)
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'live';digest=self.protocol.digest(self.bundle)
            rows=caller.phase(self.bundle,digest,out,b,self.counter,time.monotonic()+90)
            events=[json.loads(x) for x in (out/'events.jsonl').read_text().splitlines()]
            proof=verify_chunk(self.bundle,rows,events,self.counter)
            self.assertEqual(len(b.calls),4);self.assertEqual(len(proof['call_ids']),4)
            self.assertTrue(all(r['category']=='full' and r['turns']==2 for r in rows))
            self.assertTrue(json.loads((out/'complete.json').read_text())['scripted'])
            self.assertEqual(b.admitted,[([28672]*16,8096)])
            self.assertEqual(b.calls[0]['max_tokens'],6000);self.assertEqual(b.calls[2]['max_tokens'],6000)
            self.assertNotEqual(b.calls[0]['messages'],b.calls[2]['messages'])
            self.assertEqual(b.calls[0]['messages'][0],b.calls[2]['messages'][0])
            self.assertLessEqual(proof['max_completion'],8192)
            self.assertLessEqual(proof['max_context'],24576)
            with self.assertRaises(ValueError): caller.phase(self.bundle,digest,out,b,self.counter,time.monotonic()+90)
            self.assertEqual(len(b.calls),4)

    def test_unknown_second_turn_retains_reservation_and_stops_without_retry(self):
        b=ScriptedBackend(self.counter,fail_at=2)
        with tempfile.TemporaryDirectory() as t:
            rows=caller.phase(self.bundle,self.protocol.digest(self.bundle),Path(t)/'live',b,self.counter,time.monotonic()+90)
        self.assertEqual(len(b.calls),2);self.assertEqual(len(b.reserved),2)
        self.assertIsNone(rows[0]['generation_tokens']);self.assertEqual(rows[0]['category'],'provider')
        self.assertEqual(len(rows[0]['reservation_labels']),2)
        self.assertEqual(rows[1]['category'],'budget');self.assertIsNone(rows[1]['call_id'])

    def test_truncation_is_not_a_solve_or_retry(self):
        b=ScriptedBackend(self.counter,truncate=True)
        with tempfile.TemporaryDirectory() as t:
            rows=caller.phase(self.bundle,self.protocol.digest(self.bundle),Path(t)/'live',b,self.counter,time.monotonic()+90)
        self.assertEqual(len(b.calls),2)
        self.assertTrue(all(r['category']=='truncation' and r['semantic_reward'] is None for r in rows))

    def test_execute_refuses_unsealed_private_inventory_before_backend_or_route(self):
        with tempfile.TemporaryDirectory() as t:
            inputs=Path(t)/'inputs.json';inputs.write_text(json.dumps(self.bundle))
            args=SimpleNamespace(inputs=inputs,inputs_sha256=self.protocol.digest(self.bundle),prior=[],
                case_audit=Path(t)/'missing-audit',case_audit_sha256='0'*64)
            with patch.object(caller,'LIVE_CASE_AUDIT_SHA256',None), patch.object(caller,'LiveBackend') as backend:
                with self.assertRaisesRegex(ValueError,'unsealed'):
                    caller.execute(time.monotonic()+90,args)
                backend.assert_not_called()

    def test_execute_refuses_wrong_sealed_inventory_before_backend_or_route(self):
        with tempfile.TemporaryDirectory() as t:
            inputs=Path(t)/'inputs.json';inputs.write_text(json.dumps(self.bundle))
            args=SimpleNamespace(inputs=inputs,inputs_sha256=self.protocol.digest(self.bundle),prior=[],
                case_audit=Path(t)/'missing-audit',case_audit_sha256='0'*64)
            with patch.object(caller,'LIVE_CASE_AUDIT_SHA256','a'*64), patch.object(caller,'LiveBackend') as backend:
                with self.assertRaisesRegex(ValueError,'sealed case audit differs'):
                    caller.execute(time.monotonic()+90,args)
                backend.assert_not_called()

    def test_four_original_chunks_replay_but_scripted_evidence_cannot_enter_live_assembly(self):
        from assemble import load_live_chunk
        all_rows=[];all_ids=[]
        with tempfile.TemporaryDirectory() as t:
            for index in range(4):
                frozen=self.protocol.bundle(index);parent=Path(t)/str(index);parent.mkdir()
                (parent/'inputs.json').write_text(json.dumps(frozen))
                out=parent/'live';b=ScriptedBackend(self.counter)
                rows=caller.phase(frozen,self.protocol.digest(frozen),out,b,self.counter,time.monotonic()+90)
                events=[json.loads(x) for x in (out/'events.jsonl').read_text().splitlines()]
                proof=verify_chunk(frozen,rows,events,self.counter)
                all_rows+=rows;all_ids+=proof['response_ids']
                with self.assertRaisesRegex(ValueError,'live frozen chunk'):
                    load_live_chunk(index,out,self.counter)
        self.assertEqual([r['attempt_id'] for r in all_rows],
                         [j['attempt_id'] for j in self.protocol.schedule('screen')])
        self.assertEqual(len(set(all_ids)),16)


if __name__=='__main__':unittest.main()
