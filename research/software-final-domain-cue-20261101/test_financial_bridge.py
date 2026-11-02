"""Offline guard/constructor/quote controls. No private case, billing or model calls."""
import hashlib,json,tempfile,unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
import financial_bridge as b
g=b.gate

class BridgeTests(unittest.TestCase):
    def test_unsealed_refuses_before_args_or_private_io(self):
        class Bomb:
            def __getattr__(self,n):raise AssertionError('argument accessed')
        with patch.object(Path,'read_bytes',side_effect=AssertionError('private read')),patch.object(b,'load',side_effect=AssertionError('provider load')):
            with self.assertRaisesRegex(ValueError,'unsealed'):b.original_backend(Bomb())

    def test_confirmation_refuses_before_private_io(self):
        with patch.object(g,'CASE_AUDIT_SHA256','a'*64),patch.object(g,'LATEST_CLOSED_AUDIT_SHA256','b'*64),patch.object(Path,'read_bytes',side_effect=AssertionError('private read')):
            with self.assertRaisesRegex(ValueError,'confirmation remains closed'):g.require_case(NS(phase='confirmation'))

    def test_wrong_audit_lease_before_inventory(self):
        args=NS(phase='screen',expected_source='a'*40,case_audit_sha256='c'*64)
        with patch.object(g,'CASE_AUDIT_SHA256','a'*64),patch.object(g,'LATEST_CLOSED_AUDIT_SHA256','b'*64),patch.object(g,'operating_seconds'),patch.object(g,'source_guard'),patch.object(g,'verify_inventory',side_effect=AssertionError('inventory')):
            with self.assertRaisesRegex(ValueError,'exact source-bound'):g.require_case(args)

    def test_public_source_pins_match_originals(self):
        b.verify_pins()
        pins=json.loads(Path(b.__file__).with_name('financial-source-pins.json').read_text())
        self.assertEqual(len(pins),6)
        self.assertIn('scripts/allocation_amendment.py',pins)

    def test_changed_financial_pin_refused(self):
        with patch.object(b.hashlib,'sha256',return_value=NS(hexdigest=lambda:'0'*64)):
            with self.assertRaisesRegex(ValueError,'protection changed'):b.verify_pins()

    def test_constructor_forwards_exact_amendment_and_artifacts(self):
        args=NS(expected_source='a'*40,receipt=object(),reconciliation=object(),tokenizer=object(),amendment_sha256='b'*64)
        backend=NS(scripted=False);ctor=Mock(return_value=backend);case=object()
        with patch.object(g,'require_case',return_value=case),patch.object(g,'source_guard') as source,patch.object(g,'operating_seconds'),patch.object(b,'load',return_value=NS(LiveBackend=ctor)):
            self.assertEqual(b.original_backend(args),(backend,case))
        ctor.assert_called_once_with(args.receipt,args.reconciliation,args.tokenizer,args.amendment_sha256)
        source.assert_called_once_with(args.expected_source)

    def test_failed_case_never_loads_constructor(self):
        with patch.object(g,'require_case',side_effect=ValueError('closed')),patch.object(b,'load') as load:
            with self.assertRaisesRegex(ValueError,'closed'):b.original_backend(NS())
        load.assert_not_called()

    def fake(self,tmp,remaining='1',credit='1'):
        ledger=Path(tmp)/'ledger';ledger.write_bytes(b'kept reservations\n')
        receipt=Path(tmp)/'receipt';receipt.write_bytes(b'existing receipt')
        budget=NS(ledger=ledger,path=receipt,cap=Decimal('12'),ledger_prefix=ledger.read_bytes(),receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest(),_reserved=Mock(return_value=Decimal('12')-Decimal(remaining)))
        return NS(budget=budget,credit=Decimal(credit),frozen={'provider':{'pricing':{'input':'.2','output':'2.5'}}},admit=Mock())

    def test_phase_fits_but_complete_pair_refused_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            original=self.fake(tmp,remaining='.6');before=original.budget.ledger.read_bytes()
            quote=b.load('bridge_test_quote',b.ROOT/'scripts/stage-phase-admission.py')
            self.assertTrue(quote.admit(16,[28672]*16,8096,original.frozen['provider']['pricing'],'.6')['admitted'])
            with self.assertRaisesRegex(ValueError,'screen and conditional confirmation'):b.preflight_complete_plan(original,123)
            self.assertEqual(original.budget.ledger.read_bytes(),before);original.admit.assert_not_called()

    def test_actual_credit_limits_pair_independently(self):
        with tempfile.TemporaryDirectory() as tmp:
            original=self.fake(tmp,remaining='1.9',credit='.5')
            with self.assertRaisesRegex(ValueError,'actual credit'):b.preflight_complete_plan(original,123)
            original.admit.assert_not_called()

    def test_pair_then_original_phase_admission_no_reservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            original=self.fake(tmp);before=original.budget.ledger.read_bytes()
            result=b.preflight_complete_plan(original,123)
            self.assertEqual(result['calls'],32);self.assertEqual(Decimal(result['quoted_usd']),Decimal('.91429888'))
            self.assertFalse(result['reservation_performed']);self.assertFalse(result['execution_authorized'])
            original.admit.assert_called_once_with([28672]*16,8096,123)
            self.assertEqual(original.budget.ledger.read_bytes(),before)

    def test_original_phase_guard_failure_propagates(self):
        with tempfile.TemporaryDirectory() as tmp:
            original=self.fake(tmp);original.admit.side_effect=ValueError('original cumulative guard')
            with self.assertRaisesRegex(ValueError,'original cumulative guard'):b.preflight_complete_plan(original,123)

    def test_ledger_or_receipt_lease_change_refused(self):
        for change in ('ledger','receipt','missing'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as tmp:
                original=self.fake(tmp)
                if change=='ledger':original.budget.ledger.write_bytes(b'new reservation\n')
                elif change=='receipt':original.budget.path.write_bytes(b'changed')
                else:original.budget.receipt_sha256=None
                with self.assertRaisesRegex(ValueError,'exact existing accounting leases'):b.preflight_complete_plan(original,123)
                original.admit.assert_not_called()

    def chain(self,tmp):
        # Synthetic metadata only. No actual study/case input is generated.
        manifest=json.loads(Path(g.__file__).with_name('closed-method-manifest.json').read_text())
        pairs=[['synthetic-previous',1]];parent=None
        for kind,task,seed,key in (
            ('failure-advice-case-audit','software_repair-ignore-d2',3160000,None),
            ('preserve-first-case-audit','software_repair-ignore-d3',3180000,'preserve_first'),
            ('top-level-note-case-audit','software_repair-ignore-d3',3200000,'top_level'),
            ('entry-order-review-case-audit','software_repair-ignore-d3',3220000,'entry_order'),
            ('final-domain-cue-screen-case-audit','software_repair-ignore-d3',9999999,None)):
            value=dict(kind=kind,task_id=task,new_seed=seed,prior_task_seed_pairs=sorted(pairs),prior_inventory_sha256=g.digest(sorted(pairs)))
            if key:value['method_sha256']=manifest[key]
            if parent:value.update(parent_audit_path=str(parent),parent_audit_sha256=g.sha(parent))
            if kind=='final-domain-cue-screen-case-audit':
                value.update(method_sha256=g.method_hashes(),sampling=g.SAMPLING,limits=g.LIMITS);value['jobs']=g.jobs_for(value)
            path=Path(tmp)/kind;path.write_text(json.dumps(value));parent=path;pairs.append([task,seed])
        return path,value

    def test_full_synthetic_chain_requires_oldest_to_newest_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            path,value=self.chain(tmp);args=NS(phase='screen',expected_source='a'*40,case_audit_sha256=g.sha(path),case_audit=path)
            with patch.object(g,'CASE_AUDIT_SHA256',g.sha(path)),patch.object(g,'LATEST_CLOSED_AUDIT_SHA256',value['parent_audit_sha256']),patch.object(g,'source_guard'),patch.object(g,'operating_seconds'),patch.object(g,'verify_inventory',return_value={'verified':True}) as replay:
                result=g.require_case(args)
            self.assertEqual(len(result['jobs']),8)
            self.assertEqual([x.args[1]['seed'] for x in replay.call_args_list],[3160000,3180000,3200000,3220000,9999999])

    def test_dropped_prior_case_rejected_before_any_inventory_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path,value=self.chain(tmp);value['prior_task_seed_pairs']=value['prior_task_seed_pairs'][1:];value['prior_inventory_sha256']=g.digest(value['prior_task_seed_pairs']);path.write_text(json.dumps(value))
            args=NS(phase='screen',expected_source='a'*40,case_audit_sha256=g.sha(path),case_audit=path)
            with patch.object(g,'CASE_AUDIT_SHA256',g.sha(path)),patch.object(g,'LATEST_CLOSED_AUDIT_SHA256',value['parent_audit_sha256']),patch.object(g,'source_guard'),patch.object(g,'operating_seconds'),patch.object(g,'verify_inventory') as replay:
                with self.assertRaisesRegex(ValueError,'prior cases dropped'):g.require_case(args)
            replay.assert_not_called()

if __name__=='__main__':unittest.main()
