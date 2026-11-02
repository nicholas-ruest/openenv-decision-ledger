"""Pure entry/receipt boundaries. No real backend, private cases or model calls."""
import copy,json,tempfile,unittest,os
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
import case_worker as w


class WorkerTests(unittest.TestCase):
    def args(self,tmp):return NS(phase='screen',expected_source='a'*40,output=Path(tmp)/'phase',worker_qualification=Path(tmp)/'receipt',worker_qualification_sha256='c'*64)
    def test_unsealed_before_args_private_io_native_or_credentials(self):
        class Bomb:
            def __getattr__(self,k):raise AssertionError('argument accessed')
        with patch.object(w,'components',side_effect=AssertionError('Native')),patch.object(Path,'read_text',side_effect=AssertionError('private read')):
            with self.assertRaisesRegex(ValueError,'unsealed'):w.supervise(Bomb())
            with self.assertRaisesRegex(ValueError,'unsealed'):w.worker_entry(0,Bomb(),0)

    def receipt(self):
        return dict(kind='case_bound_original_worker_qualification',method_sha256={'f':'d'},original_supervisor_sha256=w.support.PIN,
            scripted_supervisor_binding_verified=True,independent_parent_raw_replay_verified=True,
            native_and_tokenizer_initialized_after_fork=True,actual_backend_constructed=False,
            synthetic_provider_only=True,assigned=8,synthetic_calls=16,unknown_usage_calls=0,max_inflight=2,max_reserving=1)

    def test_receipt_binds_exact_methods_original_supervisor_and_typed_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.args(tmp);value=self.receipt();args.worker_qualification.write_text(json.dumps(value))
            with patch.multiple(w.gate,CASE_AUDIT_SHA256='a'*64,LATEST_CLOSED_AUDIT_SHA256='b'*64,WORKER_QUALIFICATION_SHA256='c'*64),patch.object(w.gate,'source_guard'),patch.object(w.gate,'operating_seconds',return_value=1200),patch.object(w.gate,'sha',return_value='c'*64),patch.object(w.gate,'method_hashes',return_value={'f':'d'}):
                self.assertEqual(w.require_worker(args),value)
                for key,new in [('method_sha256',{}),('original_supervisor_sha256','bad'),('actual_backend_constructed',True),('synthetic_provider_only',False),('assigned',True),('max_inflight',3),('unknown_usage_calls',1)]:
                    bad=copy.deepcopy(value);bad[key]=new;args.worker_qualification.write_text(json.dumps(bad))
                    with self.assertRaises(ValueError):w.require_worker(args)
                args.worker_qualification.write_text(json.dumps(value));args.phase='confirmation'
                with self.assertRaisesRegex(ValueError,'confirmation'):w.require_worker(args)

    def test_stale_reconciliation_constructor_never_reaches_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.args(tmp);phase=Mock();prepare=Mock(side_effect=ValueError('synthetic stale reconciliation'))
            with patch.object(w,'require_worker'),patch.object(w.support,'require_fresh_parent',return_value={}),patch.object(w.support,'write'),patch.object(w,'components',return_value=NS(transport=NS(prepare=prepare),phase=phase)):
                with self.assertRaisesRegex(ValueError,'stale'):w.worker_entry(100,args,os.getppid())
            prepare.assert_called_once_with(args);phase.assert_not_called()

    def test_factory_phase_deadline_and_parent_forwarding(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.args(tmp);backend=object();prepare=Mock(return_value=backend)
            phase=Mock(return_value=([],{'complete':True},{'replay_only':True}));write=Mock()
            with patch.object(w,'require_worker'),patch.object(w.support,'require_fresh_parent',return_value={}),patch.object(w.support,'write',write),patch.object(w,'components',return_value=NS(transport=NS(prepare=prepare),phase=phase)):
                self.assertEqual(w.worker_entry(100,args,os.getppid()),0)
            prepare.assert_called_once_with(args);phase.assert_called_once_with(args,backend,args.output,100)
            self.assertFalse(write.call_args_list[-1].args[1]['selection_passed'])

    def test_fresh_parent_and_archive_refusal_before_supervisor(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.args(tmp);args.output.mkdir()
            with patch.object(w,'require_worker'),patch.object(w.support,'require_fresh_parent',return_value={}),patch.object(w.gate,'operating_seconds',return_value=1200),patch.object(w.support,'supervisor') as supervisor:
                with self.assertRaisesRegex(ValueError,'fresh archive'):w.supervise(args)
            supervisor.assert_not_called()

if __name__=='__main__':unittest.main()
