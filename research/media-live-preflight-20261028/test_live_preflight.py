import copy
from datetime import datetime,timezone,timedelta
from decimal import Decimal
import importlib.util
from pathlib import Path
import unittest

from media_protocol import digest
from test_trajectory_audit import fixture_data
from live_preflight import preview


ROOT=Path(__file__).resolve().parent.parent
path=ROOT/'software-stage-runner-20261027/scripts/stage-phase-admission.py'
if not path.exists():path=ROOT.parent/'scripts/stage-phase-admission.py'
spec=importlib.util.spec_from_file_location('existing_admission',path);AD=importlib.util.module_from_spec(spec);spec.loader.exec_module(AD)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.plan=fixture_data()[1];self.now=datetime(2026,10,28,12,tzinfo=timezone.utc);stamp=self.now.isoformat()
        # Entirely fictional accounting fixture; never an actual account ledger.
        self.receipt={'allocation_id':'existing-fixture','screen_cap_usd':'2','prior_spend_usd':'10','total_authorized_usd':'100','prepaid_balance_usd':'5','checked_at':stamp}
        self.ledger=[{'label':'previous-fixture','usd':'.25','prompt_bound':100,'generation_bound':100}]
        self.inventory={'allocation_id':'existing-fixture','screen_cap_usd':'2','prior_spend_usd':'10','parent_file_hashes':{'fixture-parent':digest('parent')}}
        self.observation={'evidence_kind':'live_reconciled_snapshot','actual_credit_usage_verified':True,'all_existing_receipts_reconciled':True,'observed_at':stamp,
                          'parent_file_hashes':copy.deepcopy(self.inventory['parent_file_hashes']),'prior_spend_usd':'10','reserved_usd':'.25','prepaid_balance_usd':'5'}
        self.provider={'observed_at':stamp,'catalog_row':{'id':'Qwen/Qwen3.8-27B','provider':{'provider':'deepinfra','status':'live','pricing':{'input':.2,'output':2.5}}}}
        self.fingerprint=digest(self.provider['catalog_row']);self.bind()
    def bind(self):self.observation.update(receipt_sha256=digest(self.receipt),ledger_sha256=digest(self.ledger))
    def run_preview(self):return preview(self.plan,'screen',self.receipt,self.ledger,self.inventory,self.observation,self.provider,self.fingerprint,now=self.now,admission_module=AD)
    def test_shared_output_quote_no_execution_authority(self):
        r=self.run_preview();expected=(Decimal(512*8192)*Decimal('.2')+Decimal(16*4096)*Decimal('2.5'))*Decimal('1.10')/Decimal(1000000)
        self.assertEqual(Decimal(r['complete_phase_quoted_usd']),expected);self.assertTrue(r['budget_feasible']);self.assertFalse(r['execution_authorized']);self.assertFalse(r['reservation_performed']);self.assertNotIn('admitted',r)
    def test_insufficient_remaining_never_shrinks_phase(self):
        self.ledger[0]['usd']='1.9';self.observation['reserved_usd']='1.9';self.bind();r=self.run_preview()
        self.assertFalse(r['budget_feasible']);self.assertEqual(r['calls_bound'],512)
    def test_synthetic_and_nested_scripted_records_rejected(self):
        for marker in ({'callbacks_synthetic':True},{'nested':{'provider_fields_synthetic':True}},{'scripted_provider_records':31}):
            previous=copy.deepcopy(self.provider);self.provider.update(marker)
            with self.assertRaises(ValueError):self.run_preview()
            self.provider=previous
    def test_stale_future_naive_timestamps_rejected(self):
        for stamp in ((self.now-timedelta(hours=3)).isoformat(),(self.now+timedelta(seconds=1)).isoformat(),'2026-10-28T12:00:00'):
            self.receipt['checked_at']=stamp;self.observation['observed_at']=stamp;self.bind()
            with self.assertRaises(ValueError):self.run_preview()
    def test_changed_cap_identity_and_prior_reset_rejected(self):
        for key,value in [('screen_cap_usd','1.5'),('allocation_id','new-fixture'),('prior_spend_usd','0')]:
            previous=self.receipt[key];self.receipt[key]=value;self.bind()
            with self.assertRaises(ValueError):self.run_preview()
            self.receipt[key]=previous
    def test_actual_usage_attestation_and_parent_inventory_required(self):
        for key,value in [('actual_credit_usage_verified',False),('all_existing_receipts_reconciled',False),('evidence_kind','synthetic_integration'),('parent_file_hashes',{})]:
            previous=self.observation[key];self.observation[key]=value
            with self.assertRaises(ValueError):self.run_preview()
            self.observation[key]=previous
    def test_freshening_timestamp_alone_does_not_refresh_binding(self):
        self.receipt['checked_at']=(self.now-timedelta(seconds=1)).isoformat()
        with self.assertRaises(ValueError):self.run_preview()
    def test_duplicate_and_negative_reservations_rejected(self):
        self.ledger.append(copy.deepcopy(self.ledger[0]));self.bind()
        with self.assertRaises(ValueError):self.run_preview()
        self.ledger.pop();self.ledger[0]['usd']='-1';self.bind()
        with self.assertRaises(ValueError):self.run_preview()
    def test_changed_provider_prices_route_fingerprint_rejected(self):
        for key,value in [('provider','other'),('status','offline'),('pricing',{'input':.2,'output':4})]:
            old=copy.deepcopy(self.provider['catalog_row']['provider']);self.provider['catalog_row']['provider'][key]=value
            with self.assertRaises(ValueError):self.run_preview()
            self.fingerprint=digest(self.provider['catalog_row'])
            with self.assertRaises(ValueError):self.run_preview()
            self.provider['catalog_row']['provider']=old;self.fingerprint=digest(self.provider['catalog_row'])
    def test_missing_ledger_or_receipt_binding_rejected(self):
        for key in ('receipt_sha256','ledger_sha256'):
            old=self.observation[key];self.observation[key]='0'*64
            with self.assertRaises(ValueError):self.run_preview()
            self.observation[key]=old
    def test_closed_allocation_and_nonfinite_values_rejected(self):
        self.receipt['closed_for_new_calls']=True;self.bind()
        with self.assertRaises(ValueError):self.run_preview()
        self.receipt.pop('closed_for_new_calls')
        for value in ('NaN','Infinity',True):
            self.receipt['prepaid_balance_usd']=value;self.bind()
            with self.assertRaises(ValueError):self.run_preview()
    def test_inputs_unchanged(self):
        before=digest([self.receipt,self.ledger,self.inventory,self.observation,self.provider]);self.run_preview()
        self.assertEqual(before,digest([self.receipt,self.ledger,self.inventory,self.observation,self.provider]))


if __name__=='__main__':unittest.main()
