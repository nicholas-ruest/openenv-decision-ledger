from datetime import datetime
import copy
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch,Mock
from zoneinfo import ZoneInfo
import guarded_transport as b
import assemble_qualification as assembly
import test_finite_qualification as fixture


class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.FiniteTests.setUpClass();cls.counter=fixture.FiniteTests.counter
        cls.replies=copy.deepcopy(fixture.FiniteTests.good)
        for r in cls.replies:r['choices'][0]['finish_reason']='length'

    def test_unsealed_guard_precedes_source_clock_backend_and_private_reads(self):
        with patch.object(b.p,'load',side_effect=AssertionError('no backend')),patch.object(b,'verify_clean_source',side_effect=AssertionError('no source')):
            with self.assertRaises(ValueError):b.guarded_backend(SimpleNamespace())

    def test_existing_backend_parameters_and_unchanged_admission_delegated(self):
        original=Mock(counter=self.counter)
        args=SimpleNamespace(expected_source='frozen',receipt=Path('receipt'),reconciliation=Path('audit'),tokenizer=Path('tokenizer'),amendment_sha256='amendment')
        with patch.object(b,'require_live_ready'),patch.object(b,'verify_clean_source'),patch.object(b,'operating_seconds',return_value=1200),patch.object(b.p,'load',return_value=SimpleNamespace(LiveBackend=Mock(return_value=original))) as loader:
            wrapper=b.guarded_backend(args)
        self.assertIs(wrapper.original,original)
        self.assertEqual(loader.call_args.args[1],'research/software-public-pass-confirmation-20261031/caller.py')
        deadline=time.monotonic()+1200;wrapper.admit([28672]*8,6000,deadline)
        original.admit.assert_called_once_with([28672]*16,8096,deadline)
        with self.assertRaises(ValueError):wrapper.admit([28672]*8,6000,deadline)

    def test_exact_one_call_per_original_reserved_assignment_even_after_failure(self):
        import matched_protocol as protocol
        original=Mock(counter=self.counter);original.call.side_effect=TimeoutError('synthetic unknown usage')
        wrapper=b.ConservativeBackend(original);deadline=time.monotonic()+1200
        wrapper.admit([28672]*8,6000,deadline);job=protocol.jobs('screen')[0];label=job['attempt_id']+':0'
        payload=dict(b.p.SAMPLING,messages=[],max_tokens=6000)
        with self.assertRaises(ValueError):wrapper.call(payload,1,job)
        wrapper.reserve(label,28672,6000,deadline)
        with self.assertRaises(TimeoutError):wrapper.call(payload,1,job)
        with self.assertRaises(ValueError):wrapper.call(payload,1,job)
        with self.assertRaises(ValueError):wrapper.reserve(label,28672,6000,deadline)
        with self.assertRaises(ValueError):wrapper.reserve('arbitrary',28672,6000,deadline)
        self.assertIn(label,wrapper.labels);self.assertEqual(original.call.call_count,1)

    def test_fixed_stop_and_changed_dependency_guard(self):
        tz=ZoneInfo('America/Toronto')
        self.assertEqual(b.operating_seconds(datetime(2026,11,1,22,59,tzinfo=tz)),60)
        self.assertEqual(b.operating_seconds(datetime(2026,11,1,9,tzinfo=tz)),1200)
        with self.assertRaises(ValueError):b.operating_seconds(datetime(2026,11,1,23,tzinfo=tz))
        with self.assertRaises(ValueError):b.operating_seconds(datetime(2026,11,1,9))
        b.verify_dependencies()
        with patch.object(b,'verify_dependencies',side_effect=ValueError('changed dependency')):
            with self.assertRaises(ValueError):b.supervise_qualification(fixture.Backend(self.replies),self.counter,Path('unused'),1)

    def test_real_whole_phase_supervisor_and_independent_archive_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'phase'
            result=b.supervise_qualification(fixture.Backend(self.replies),self.counter,out,120)
            self.assertEqual(result['status'],'completed');self.assertTrue(result['shutdown_verified'])
            self.assertTrue(result['finished_before_deadline']);self.assertFalse(result['remote_cancellation_attested'])
            report=assembly.assemble(out,self.counter)
            self.assertTrue(report['complete']);self.assertEqual(report['independently_replayed'],8)
            self.assertFalse(report['selection_passed'])
            with self.assertRaises(ValueError):b.supervise_qualification(fixture.Backend(self.replies),self.counter,out,120)
            records=out/'records.jsonl';rows=[json.loads(x) for x in records.read_text().splitlines()]
            rows[0]['category']='full';records.write_text(''.join(json.dumps(x)+'\n' for x in rows))
            with self.assertRaises(ValueError):assembly.assemble(out,self.counter)

    def test_unknown_usage_failure_archive_never_gets_fitness_or_refund(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'failure';backend=fixture.Backend([TimeoutError('synthetic failure')])
            b.finite.run(backend,self.counter,out,time.monotonic()+1200)
            report=assembly.assemble(out,self.counter)
            self.assertFalse(report['complete']);self.assertFalse(report['fitness_eligible'])
            self.assertEqual(report['rows'][0]['unknown_usage'],True)
            self.assertEqual(sum(not r['recorded'] for r in report['rows']),7)
            self.assertEqual(len(backend.reservations),1)
            (out/'complete.json').unlink()
            self.assertFalse(assembly.assemble(out,self.counter)['complete'])

    def test_supervisor_timeout_cannot_become_success_or_remote_cancellation(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=b.supervise_qualification(fixture.Backend(self.replies),self.counter,Path(tmp)/'timeout',.01)
            self.assertEqual(result['status'],'timed_out');self.assertTrue(result['shutdown_verified'])
            self.assertFalse(result['remote_cancellation_attested'])
        with self.assertRaises(ValueError):b.supervise_qualification(SimpleNamespace(scripted=False),self.counter,Path('unused'),1)


if __name__=='__main__':unittest.main()
