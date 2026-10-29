"""Scripted native integration only. No credentials, actual funds or model calls."""
import argparse
import ast
import json
from pathlib import Path
import tempfile
import sys
import time
import unittest
from caller import ROOT, load, modules, phase, reconciliation


class ScriptedBackend:
    scripted = True
    def __init__(self, counter, denied=False, fail_at=None):
        self.counter = counter; self.denied = denied; self.fail_at = fail_at
        self.calls = 0; self.reservations = []; self.admissions = []
    def admit(self, bounds, generation, deadline):
        self.admissions.append((len(bounds), generation))
        if self.denied: raise ValueError('fictional admission denied')
    def reserve(self, label, prompt, generation, deadline):
        self.reservations.append(label)
    def check_reply(self, response): pass
    def check_message(self, message): pass
    def call(self, payload, timeout, job):
        self.calls += 1
        if self.calls == self.fail_at: raise TimeoutError('fictional provider failure')
        from repair_env.tasks import make_task
        from function_edit import TARGETS
        source = make_task(job['task_id'], job['seed']).reference_source
        if job['arm'] == 'function_block_available':
            node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == TARGETS[job['task_id']])
            source = ''.join(source.splitlines(keepends=True)[node.lineno-1:node.end_lineno])
        content = json.dumps({'content': source})
        return dict(id='scripted-'+job['attempt_id'],
            usage=dict(prompt_tokens=self.counter.context(payload['messages']), completion_tokens=self.counter.count(content)),
            choices=[dict(message=dict(role='assistant', content=content), finish_reason='stop')])


class CallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cache = tempfile.TemporaryDirectory()
        protocol, _ = modules(); cls.protocol = protocol
        cls.bundle = protocol.bundle()
        cls.digest = protocol.digest(cls.bundle)
        sys.path.insert(0, str(ROOT/'integrations/openenv-arena'))
        helper = load('caller_control_tokenizer', ROOT/'integrations/openenv-arena/scripts/calibrate.py')
        cls.counter = helper.load_counter(argparse.Namespace(accounting='arena',
            tokenizer_json=Path('/home/ruv/arena-tokenizer.json'),
            tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
    @classmethod
    def tearDownClass(cls): cls.cache.cleanup()
    def test_four_chunks_partition_all_sixteen_assignments_at_native_budget(self):
        bundles=[self.protocol.bundle(i) for i in range(4)]
        jobs=[j for b in bundles for j in b['screen_jobs']]
        self.assertEqual(jobs,self.protocol.schedule('screen'))
        self.assertEqual(len({j['attempt_id'] for j in jobs}),16)
        self.assertTrue(all(b['completion_with_observations']==8192 and b['context']==24576 for b in bundles))
        self.assertTrue(all(b['sampling']['max_tokens']==8096 for b in bundles))
        self.assertTrue(all(len(b['screen_jobs'])==4 and b['all_screen_jobs']==jobs for b in bundles))
        with self.assertRaises(ValueError):self.protocol.bundle(True)
    def test_live_admission_quotes_whole_sixteen_call_study_not_only_four_call_chunk(self):
        from caller import LiveBackend
        from types import SimpleNamespace
        from decimal import Decimal
        with tempfile.TemporaryDirectory() as tmp:
            ledger=Path(tmp)/'fictional-ledger';ledger.write_text('')
            backend=object.__new__(LiveBackend)
            backend.budget=SimpleNamespace(ledger=ledger,cap=Decimal('.10'))
            backend.credit=Decimal('1');backend.frozen={'provider':{'pricing':{'input':1,'output':1}}}
            with self.assertRaises(ValueError):backend.admit([100]*4,8096,time.monotonic()+30)
            self.assertEqual(ledger.read_text(),'')
    def test_complete_native_scripted_phase_preserves_assignments_and_frozen_requests(self):
        backend = ScriptedBackend(self.counter)
        with tempfile.TemporaryDirectory() as tmp:
            rows = phase(self.bundle, self.digest, Path(tmp)/'out', backend, self.counter, time.monotonic()+90)
            self.assertEqual(len(rows), 4); self.assertEqual(backend.calls, 4)
            self.assertEqual(backend.admissions, [(4,8096)])
            self.assertEqual(len(set(backend.reservations)), 4)
            self.assertEqual([r['attempt_id'] for r in rows], [j['attempt_id'] for j in self.bundle['screen_jobs']])
            self.assertTrue(all(r['category']=='full' for r in rows))
            summary = json.loads((Path(tmp)/'out/complete.json').read_text())
            self.assertTrue(summary['scripted']); self.assertFalse(summary['model_improvement'])
            with self.assertRaises(ValueError): phase(self.bundle,self.digest,Path(tmp)/'out',backend,self.counter,time.monotonic()+30)
    def test_whole_phase_denial_happens_before_any_reservation_or_call(self):
        backend = ScriptedBackend(self.counter, denied=True)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'denied'
            with self.assertRaises(ValueError): phase(self.bundle,self.digest,out,backend,self.counter,time.monotonic()+30)
            self.assertEqual(backend.calls,0); self.assertEqual(backend.reservations,[]); self.assertFalse(out.exists())
    def test_provider_timeout_never_retries_or_drops_remaining_assigned_denominator(self):
        backend = ScriptedBackend(self.counter, fail_at=3)
        with tempfile.TemporaryDirectory() as tmp:
            rows = phase(self.bundle,self.digest,Path(tmp)/'failed',backend,self.counter,time.monotonic()+90)
            self.assertEqual(backend.calls,3); self.assertEqual(len(rows),4)
            self.assertEqual(rows[2]['category'],'provider'); self.assertIsNone(rows[2]['generation_tokens'])
            self.assertTrue(all(r['category']=='budget' and r['call_id'] is None and r['reservation_label'] is None for r in rows[3:]))
            self.assertEqual(len(backend.reservations),3)
            events = [json.loads(x) for x in (Path(tmp)/'failed/events.jsonl').read_text().splitlines()]
            failures = [e for e in events if e['event']=='failure']
            self.assertEqual(len(failures),1)
            self.assertEqual(failures[0]['code'],'timeout')
            self.assertEqual(failures[0]['stage'],'provider')
            self.assertNotIn('fictional provider failure',json.dumps(failures))
    def test_changed_input_digest_refuses_calls(self):
        backend = ScriptedBackend(self.counter)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError): phase(self.bundle,'0'*64,Path(tmp)/'changed',backend,self.counter,time.monotonic()+30)
            self.assertEqual(backend.calls,0); self.assertEqual(backend.admissions,[])
    def test_real_cli_reaches_supervision_before_missing_audit_denies(self):
        import subprocess
        source=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'live';inputs=Path(tmp)/'inputs.json';inputs.write_text(json.dumps(self.bundle))
            args=[sys.executable,str(Path(__file__).with_name('caller.py')),'--execute','--expected-source',source,'--inputs',str(inputs),'--inputs-sha256',self.digest,'--receipt',str(Path(tmp)/'receipt'),'--reconciliation',str(Path(tmp)/'missing-audit'),'--tokenizer','/home/ruv/arena-tokenizer.json','--output',str(out),'--amendment-sha256','0'*64]
            subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=20)
            self.assertFalse(out.exists())
            events=[json.loads(x) for x in out.with_suffix('.supervision.jsonl').read_text().splitlines()]
            self.assertEqual(events[-1]['status'],'worker_failed');self.assertTrue(events[-1]['shutdown_verified'])
            self.assertNotEqual(events[-1]['worker_exitcode'],0)
    def test_stale_private_audit_cannot_enable_live_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'fictional-audit.json'
            path.write_text(json.dumps({'observed_at':'2000-01-01T00:00:00+00:00'}))
            with self.assertRaises(ValueError): reconciliation(path,Path(tmp)/'not-a-real-receipt')


if __name__ == '__main__': unittest.main()
