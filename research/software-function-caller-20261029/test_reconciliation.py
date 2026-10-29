"""Pure guard tests using temporary fictional receipts, never user accounts."""
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from caller import reconciliation, sha


class ReconciliationTests(unittest.TestCase):
    def fixture(self, root):
        known=[]; inventory=[]
        for index in range(2):
            p=root/('fictional-receipt-'+str(index)+'.json')
            p.write_text('{"fictional_fixture":true}')
            ledger=p.with_suffix('.reservations.jsonl');ledger.write_text('')
            known.append(dict(receipt=str(p),receipt_sha256=sha(p),ledger_sha256=sha(ledger)))
            inventory.append(dict(path=str(p),sha256=sha(p)))
        now=datetime.now(timezone.utc).isoformat()
        value=dict(observed_at=now,execution_authorized=True,receipt_inventory_complete=True,
            root_prior_not_reattested=False,errors=[],changed_files=[],carry_forward_errors=[],
            actual_billing_visual=dict(observed_at=now,automatic_recharge=False,credits_usd='31.41'),
            all_known_receipts=known,inventory=inventory)
        return value,Path(known[0]['receipt'])
    def check(self, mutate, expected_failure=True):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);value,receipt=self.fixture(root);mutate(value,root)
            audit=root/'fictional-audit.json';audit.write_text(json.dumps(value))
            if expected_failure:
                with self.assertRaises(ValueError):reconciliation(audit,receipt)
            else:self.assertEqual(reconciliation(audit,receipt),Decimal('31.41'))
    def test_complete_external_audit_uses_inventory_not_a_personal_receipt_count(self):
        self.check(lambda value,root:None,False)
    def test_omitted_and_modified_receipts_fail_before_financial_admission(self):
        self.check(lambda value,root:value['all_known_receipts'].pop())
        self.check(lambda value,root:Path(value['inventory'][0]['path']).write_text('changed'))
        self.check(lambda value,root:Path(value['all_known_receipts'][0]['receipt']).with_suffix('.reservations.jsonl').write_text('changed'))
    def test_unattested_prior_or_unauthorized_audit_cannot_enable_calls(self):
        self.check(lambda value,root:value.update(root_prior_not_reattested=True))
        self.check(lambda value,root:value.update(execution_authorized=False))


if __name__=='__main__':unittest.main()
