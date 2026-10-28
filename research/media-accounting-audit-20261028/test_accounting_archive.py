import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import verified_phase as phase
from accounting_archive import make_config,verify_archive
from observation_budget import EpisodeBudget
from test_observation_budget import SyntheticByteCounter
import test_media_durable as fixtures
from media_protocol import digest


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.PhaseTests();self.f.setUp();self.addCleanup(self.f.tmp.cleanup)
        self.counter=SyntheticByteCounter();self.config=make_config(self.counter)
    def run_phase(self,completion=4096,context=8192):
        f=self.f;self.config=make_config(self.counter,completion=completion,context=context)
        def reserve(label,history,remaining):
            f.reserve(label,history,remaining);f.ledger[-1]['prompt_bound']=self.counter.context(history)
        dispatch=f.dispatch
        def frozen_dispatch(*args):
            self.assertEqual(json.loads((f.root/'accounting.json').read_text()),self.config)
            self.assertEqual(json.loads((f.root/'claim.json').read_text())['accounting_sha256'],digest(self.config))
            return dispatch(*args)
        return phase.run_phase(f.root,f.plan,f.schema,'screen','test',100,True,lambda:f.time,f.open_env,reserve,lambda:f.ledger,frozen_dispatch,f.replay,
            accounting_factory=lambda h:EpisodeBudget(self.counter,h,completion=completion,context=context),accounting_config=self.config)
    def verify(self):
        f=self.f
        return verify_archive(f.root,f.plan,f.schema,'screen',self.config,self.counter,f.ledger,f.replay)
    def edit(self,name,mutate):
        p=self.f.root/name;obj=json.loads(p.read_text());mutate(obj);p.write_text(json.dumps(obj))
    def test_complete_raw_cost_reconstruction(self):
        expected=self.run_phase();result=self.verify();self.assertEqual(result['report'],expected);self.assertEqual(result['episodes_recomputed'],16)
        self.assertFalse(result['execution_authorized']);self.assertFalse(result['arena_wrapper_equivalent']);self.assertTrue(self.config['synthetic_counter'])
    def test_verifier_does_not_use_runtime_budget_methods(self):
        self.run_phase()
        with patch.object(EpisodeBudget,'snapshot',side_effect=AssertionError('runtime reused')),patch.object(EpisodeBudget,'observation',side_effect=AssertionError('runtime reused')):
            self.verify()
    def test_saved_cost_edit_rejected_even_with_self_consistent_report(self):
        self.run_phase()
        self.edit('00-episode.json',lambda o:o['validated']['local_accounting'].update(postreset_observation_tokens=0,completion_used=20))
        with self.assertRaisesRegex(ValueError,'recomputed accounting'):self.verify()
    def test_altered_saved_config_rejected(self):
        self.run_phase();self.edit('accounting.json',lambda o:o.update(completion_limit=8192))
        with self.assertRaisesRegex(ValueError,'saved accounting'):self.verify()
    def test_changed_trusted_config_cannot_reinterpret_old_archive(self):
        self.run_phase();self.config=make_config(self.counter,completion=3000)
        with self.assertRaises(ValueError):self.verify()
    def test_source_manifest_edit_rejected_before_root(self):
        self.config['source_sha256']['verified_phase']='0'*64
        f=self.f
        with self.assertRaisesRegex(ValueError,'source manifest'):
            phase.run_phase(f.root,f.plan,f.schema,'screen','test',100,True,lambda:f.time,f.open_env,f.reserve,lambda:f.ledger,f.dispatch,f.replay,accounting_factory=lambda h:EpisodeBudget(self.counter,h),accounting_config=self.config)
        self.assertFalse(f.root.exists());self.assertEqual(f.dispatched,[])
    def test_factory_limits_mismatch_no_dispatch(self):
        f=self.f
        with self.assertRaisesRegex(ValueError,'factory/config'):
            phase.run_phase(f.root,f.plan,f.schema,'screen','test',100,True,lambda:f.time,f.open_env,f.reserve,lambda:f.ledger,f.dispatch,f.replay,accounting_factory=lambda h:EpisodeBudget(self.counter,h,completion=3000),accounting_config=self.config)
        self.assertEqual(f.dispatched,[]);self.assertEqual(f.closed,1)
    def test_intent_accounting_edit_rejected(self):
        self.run_phase();self.edit('00-00-intent.json',lambda o:o.update(accounting_sha256='0'*64))
        with self.assertRaisesRegex(ValueError,'intent accounting'):self.verify()
    def test_raw_provider_edit_with_rehashed_envelope_rejected(self):
        self.run_phase()
        def change(o):o['payload']['response']['usage']['completion_tokens']=9;o['sha256']=digest(o['payload'])
        self.edit('00-00-provider.json',change)
        with self.assertRaisesRegex(ValueError,'provider/event'):self.verify()
    def test_overflow_native_one_cannot_be_promoted(self):
        original=self.f.open_env
        def open_env(*args):
            env=original(*args);step=env['step']
            def large(*values):
                n=step(*values)
                if n['done']:n['observation']['output']='x'*9000
                return n
            env['step']=large;return env
        self.f.open_env=open_env;self.assertEqual(self.run_phase()['counts'],{'budget':16});self.verify()
        self.edit('00-episode.json',lambda o:o['validated'].update(category='full',semantic_reward=1))
        with self.assertRaisesRegex(ValueError,'recomputed accounting'):self.verify()
    def test_nonterminal_overflow_both_limits_recomputed(self):
        original=self.f.open_env
        def open_env(*args):
            env=original(*args);step=env['step']
            def large(*values):
                n=step(*values);n['observation']['output']='x'*9000;return n
            env['step']=large;return env
        self.f.open_env=open_env;self.assertEqual(self.run_phase()['counts'],{'budget':16});self.verify()
        self.assertEqual(len(self.f.dispatched),16)
    def test_initial_overflow_zero_calls_recomputed(self):
        self.assertEqual(self.run_phase(1,1)['counts'],{'budget':16});self.verify();self.assertEqual(self.f.dispatched,[])
    def test_provider_failure_keeps_full_denominator(self):
        self.f.mode='provider';r=self.run_phase();self.assertEqual(r['counts'],{'provider':1,'full':15});self.verify()
    def test_failed_config_persistence_prevents_dispatch(self):
        save=phase.durable_new
        def fail(root,name,value):
            if name=='accounting.json':raise OSError('disk full')
            return save(root,name,value)
        with patch.object(phase,'durable_new',fail):
            with self.assertRaises(OSError):self.run_phase()
        self.assertEqual(self.f.dispatched,[]);self.assertEqual(self.f.closed,0)
    def test_duplicate_json_and_symlink_rejected(self):
        self.run_phase();p=self.f.root/'accounting.json';old=p.read_text();p.write_text('{"version":1,"version":1}')
        with self.assertRaisesRegex(ValueError,'duplicate'):self.verify()
        p.write_text(old);p.rename(self.f.root/'real-accounting.json');p.symlink_to(self.f.root/'real-accounting.json')
        with self.assertRaisesRegex(ValueError,'regular archive'):self.verify()


if __name__=='__main__':unittest.main()
