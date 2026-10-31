"""Guard-order, delegation and real local supervisor qualification; no provider."""
from datetime import datetime
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

import transport_bridge as b
import test_finite_caller as fixture
from replay_matched import verify


class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.CallerTests.setUpClass();cls.counter=fixture.CallerTests.counter

    def test_unsealed_guard_precedes_loading_source_clock_or_backend(self):
        with patch.object(b,'load',side_effect=AssertionError('no backend import')),patch.object(b,'verify_clean_source',side_effect=AssertionError('no file inspection')):
            with self.assertRaises(ValueError):b.guarded_backend(SimpleNamespace())
            with self.assertRaises(ValueError):b.require_live_supervision('unused','unused')

    def test_existing_backend_arguments_are_delegated_without_new_budget_route(self):
        args=SimpleNamespace(expected_source='frozen',receipt=Path('existing-receipt'),reconciliation=Path('existing-audit'),tokenizer=Path('existing-tokenizer'),amendment_sha256='bound-amendment')
        fake=SimpleNamespace(LiveBackend=lambda *values:values)
        with patch.object(b.finite_caller,'require_live_ready'),patch.object(b,'verify_clean_source') as clean,patch.object(b,'operating_seconds',return_value=1200),patch.object(b,'load',return_value=fake) as loader:
            result=b.guarded_backend(args)
        self.assertEqual(result,(args.receipt,args.reconciliation,args.tokenizer,args.amendment_sha256))
        clean.assert_called_once_with('frozen')
        self.assertTrue(str(loader.call_args.args[1]).endswith('software-public-pass-confirmation-20261031/caller.py'))

    def test_fixed_stop_and_supervisor_cap_do_not_change_with_host_timezone(self):
        tz=ZoneInfo('America/Toronto')
        self.assertEqual(b.operating_seconds(datetime(2026,10,31,22,59,tzinfo=tz)),60)
        self.assertEqual(b.operating_seconds(datetime(2026,10,31,17,tzinfo=tz)),1200)
        with self.assertRaises(ValueError):b.operating_seconds(datetime(2026,10,31,23,tzinfo=tz))
        with self.assertRaises(ValueError):b.operating_seconds(datetime(2026,10,31,22,59))

    def test_actual_supervisor_completes_and_replays_existing_qualification_chunk(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'control'
            result=b.supervise_qualification(0,fixture.Backend(self.counter),self.counter,out,60,
                now=datetime(2026,10,31,17,tzinfo=ZoneInfo('America/Toronto')))
            self.assertEqual(result['status'],'completed');self.assertTrue(result['shutdown_verified'])
            self.assertTrue(result['finished_before_deadline']);self.assertFalse(result['live_evidence'])
            for p in out.glob('*.trace.json'):self.assertTrue(verify(json.loads(p.read_text()),self.counter)['verified'])
            with self.assertRaises(ValueError):b.supervise_qualification(0,fixture.Backend(self.counter),self.counter,out,60)

    def test_actual_supervisor_timeout_is_not_remote_cancellation_or_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'timeout'
            result=b.supervise_qualification(0,fixture.Backend(self.counter),self.counter,out,.01,
                now=datetime(2026,10,31,17,tzinfo=ZoneInfo('America/Toronto')))
            self.assertEqual(result['status'],'timed_out');self.assertTrue(result['shutdown_verified'])
            self.assertFalse(result['remote_cancellation_attested'])

    def test_changed_dependency_and_non_scripted_qualification_are_refused(self):
        b.verify_dependencies()
        with patch.object(b,'verify_dependencies',side_effect=ValueError('changed source')):
            with tempfile.TemporaryDirectory() as tmp,self.assertRaises(ValueError):
                b.supervise_qualification(0,fixture.Backend(self.counter),self.counter,Path(tmp)/'new',1)
        with self.assertRaises(ValueError):
            b.supervise_qualification(0,SimpleNamespace(scripted=False),self.counter,Path('unused'),1)


if __name__=='__main__':unittest.main()
