"""Scripted native integration only. No credentials, actual funds or model calls."""
import argparse
import ast
import json
from pathlib import Path
import tempfile
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
        protocol.freeze(Path(cls.cache.name)/'inputs', 'scripted-caller-control')
        cls.bundle = json.loads((Path(cls.cache.name)/'inputs/inputs.json').read_text())
        cls.digest = protocol.digest(cls.bundle)
        helper = load('caller_control_tokenizer', ROOT/'integrations/openenv-arena/scripts/calibrate.py')
        cls.counter = helper.load_counter(argparse.Namespace(accounting='arena',
            tokenizer_json=Path('/home/ruv/arena-tokenizer.json'),
            tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
    @classmethod
    def tearDownClass(cls): cls.cache.cleanup()
    def test_complete_native_scripted_phase_preserves_assignments_and_frozen_requests(self):
        backend = ScriptedBackend(self.counter)
        with tempfile.TemporaryDirectory() as tmp:
            rows = phase(self.bundle, self.digest, Path(tmp)/'out', backend, self.counter, time.monotonic()+90)
            self.assertEqual(len(rows), 32); self.assertEqual(backend.calls, 32)
            self.assertEqual(backend.admissions, [(32,2048)])
            self.assertEqual(len(set(backend.reservations)), 32)
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
            self.assertEqual(backend.calls,3); self.assertEqual(len(rows),32)
            self.assertEqual(rows[2]['category'],'provider'); self.assertIsNone(rows[2]['generation_tokens'])
            self.assertTrue(all(r['category']=='budget' and r['call_id'] is None and r['reservation_label'] is None for r in rows[3:]))
            self.assertEqual(len(backend.reservations),3)
    def test_changed_input_digest_refuses_calls(self):
        backend = ScriptedBackend(self.counter)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError): phase(self.bundle,'0'*64,Path(tmp)/'changed',backend,self.counter,time.monotonic()+30)
            self.assertEqual(backend.calls,0); self.assertEqual(backend.admissions,[])
    def test_stale_private_audit_cannot_enable_live_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'fictional-audit.json'
            path.write_text(json.dumps({'observed_at':'2000-01-01T00:00:00+00:00'}))
            with self.assertRaises(ValueError): reconciliation(path,Path(tmp)/'not-a-real-receipt')


if __name__ == '__main__': unittest.main()
