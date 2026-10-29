"""Fictional receipts only; actual reservation class, no provider/model calls."""
import ast
from datetime import datetime, timezone
from decimal import Decimal
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from allocation_amendment import digest, verified_cap_ceiling


def reservation_class():
    # Execute the actual budgeting class without importing unrelated native
    # environment/provider dependencies. No copied replacement implementation.
    source = Path(__file__).with_name('repair-signal-screen.py')
    if not source.exists():
        source = Path(__file__).resolve().parents[2]/'scripts/repair-signal-screen.py'
    node = next(n for n in ast.parse(source.read_text()).body
                if isinstance(n, ast.ClassDef) and n.name == 'DollarReservations')
    ns = dict(Path=Path, json=json, datetime=datetime, timezone=timezone,
              Decimal=Decimal, threading=threading, fcntl=fcntl, os=os)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), ns)
    return ns['DollarReservations']


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.p = self.root/'fictional.json'
        before = dict(checked_at=datetime.now(timezone.utc).isoformat(),
            screen_cap_usd=2, prior_spend_usd='3.14', prepaid_balance_usd='20',
            total_authorized_usd=100, parent_receipt='fictional-parent', parent_ledger_sha256='parent')
        raw = json.dumps(before).encode(); prefix = b'{"label":"old","usd":"1.25"}\n'
        (self.root/'receipt-before.json').write_bytes(raw)
        (self.root/'ledger-before.jsonl').write_bytes(prefix)
        self.p.with_suffix('.reservations.jsonl').write_bytes(prefix)
        auth = dict(previous_cap_usd=2, added_usd=10, new_cap_usd=12,
                    previous_receipt_sha256=digest(raw), unchanged_ledger_sha256=digest(prefix))
        ap = self.root/'authorization.json'; ap.write_text(json.dumps(auth))
        self.sha = digest(ap.read_bytes()); self.value = dict(before, screen_cap_usd=12,
            allocation_amendment=dict(auth, authorization_receipt=str(ap)))
        self.write()

    def write(self): self.p.write_text(json.dumps(self.value))

    def test_explicit_digest_retains_prior_reservations_and_enforces_raised_ceiling(self):
        cls = reservation_class()
        with self.assertRaises(ValueError): cls(self.p)
        budget = cls(self.p, amendment_sha256=self.sha)
        budget.reserve('new', 1, 1, dict(input=1, output=1))
        self.assertEqual(verified_cap_ceiling(self.p, self.value, self.sha), Decimal(12))
        with self.assertRaises(ValueError): budget.reserve('new',1,1,dict(input=1,output=1))
        with self.assertRaises(ValueError): budget.reserve('too-large',20_000_000,1,dict(input=1,output=1))

    def test_changed_authority_history_or_removed_reservations_refused(self):
        for mutate in ('authority', 'history', 'ledger'):
            with self.subTest(mutate=mutate):
                target = self.root/({'authority':'authorization.json','history':'receipt-before.json','ledger':'fictional.reservations.jsonl'}[mutate])
                raw = target.read_bytes(); target.write_text('{}')
                with self.assertRaises(ValueError): verified_cap_ceiling(self.p,self.value,self.sha)
                target.write_bytes(raw)

    def test_freshness_credit_total_and_parent_guards_remain(self):
        cls=reservation_class()
        for key,value in [('checked_at','2000-01-01T00:00:00+00:00'),
                          ('prepaid_balance_usd','1'),('total_authorized_usd',15),
                          ('prior_spend_usd','0'),('parent_receipt','other'),('screen_cap_usd',13)]:
            with self.subTest(key=key):
                old=self.value[key];self.value[key]=value;self.write()
                with self.assertRaises(ValueError):cls(self.p,amendment_sha256=self.sha)
                self.value[key]=old;self.write()


if __name__ == '__main__': unittest.main()
