"""Fictional financial fixtures exercise the actual trusted reservation class."""
import ast,fcntl,hashlib,json,os,sys,tempfile,threading,unittest
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).parent
sys.path.insert(0,str(ROOT))
source=ROOT/'repair-signal-screen.py'
if not source.exists():source=ROOT.parents[1]/'scripts/repair-signal-screen.py'
sys.path.insert(0,str(source.parent))
tree=ast.parse(source.read_text())
node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='DollarReservations')
scope=dict(Path=Path,Decimal=Decimal,datetime=datetime,timezone=timezone,json=json,
           fcntl=fcntl,hashlib=hashlib,os=os,threading=threading)
exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),scope)
Reservations=scope['DollarReservations']
sha=lambda b:hashlib.sha256(b).hexdigest()

class RemainingAllocationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.receipt=self.root/'receipt.json';self.ledger=self.root/'receipt.reservations.jsonl'
        self.before=dict(checked_at=datetime.now(timezone.utc).isoformat(),screen_cap_usd=2,
                         prior_spend_usd=5,total_authorized_usd=100,prepaid_balance_usd=20,
                         parent_receipt='unchanged-parent',parent_ledger_sha256='unchanged')
        before=json.dumps(self.before).encode();prefix=b'{"label":"old-unknown-usage","usd":"1"}\n'
        auth=dict(user_instruction='add $10',previous_cap_usd=2,added_usd=10,new_cap_usd=12,
                  previous_receipt_sha256=sha(before),unchanged_ledger_sha256=sha(prefix))
        self.auth=self.root/'authorization.json'
        self.auth.write_text(json.dumps(auth))
        (self.root/'receipt-before.json').write_bytes(before)
        (self.root/'ledger-before.jsonl').write_bytes(prefix)
        self.ledger.write_bytes(prefix+b'{"label":"retained-later","usd":"3"}\n')
        self.value={**self.before,'screen_cap_usd':12,'prepaid_balance_usd':8,
                    'allocation_amendment':{**auth,'authorization_receipt':str(self.auth)}}
        self.receipt.write_text(json.dumps(self.value))
        self.pin=sha(self.auth.read_bytes())
    def tearDown(self):self.tmp.cleanup()
    def make(self,**changes):
        self.value.update(changes);self.receipt.write_text(json.dumps(self.value))
        return Reservations(self.receipt,amendment_sha256=self.pin,
            receipt_sha256=sha(self.receipt.read_bytes()),ledger_sha256=sha(self.ledger.read_bytes()))
    def test_exact_remaining_credit_admits_without_reset(self):
        original=self.ledger.read_bytes();gate=self.make()
        self.assertEqual(gate.cap,12);self.assertEqual(gate.used_snapshot,4)
        self.assertEqual(self.ledger.read_bytes(),original)
    def test_insufficient_remaining_credit_rejected(self):
        with self.assertRaises(ValueError):self.make(prepaid_balance_usd='7.99999999')
    def test_legacy_full_cap_guard_unchanged(self):
        with self.assertRaises(ValueError):Reservations(self.receipt,amendment_sha256=self.pin)
    def test_no_amendment_no_new_headroom(self):
        with self.assertRaises(ValueError):
            Reservations(self.receipt,receipt_sha256=sha(self.receipt.read_bytes()),
                         ledger_sha256=sha(self.ledger.read_bytes()))
    def test_both_exact_file_leases_required(self):
        for kw in ({'receipt_sha256':sha(self.receipt.read_bytes())},
                   {'ledger_sha256':sha(self.ledger.read_bytes())},
                   {'receipt_sha256':'0'*64,'ledger_sha256':sha(self.ledger.read_bytes())},
                   {'receipt_sha256':sha(self.receipt.read_bytes()),'ledger_sha256':'0'*64}):
            with self.subTest(kw=kw),self.assertRaises(ValueError):
                Reservations(self.receipt,amendment_sha256=self.pin,**kw)
    def test_freshness_closed_and_finite_constraints(self):
        for changes in ({'checked_at':(datetime.now(timezone.utc)-timedelta(hours=3)).isoformat()},
                        {'checked_at':(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()},
                        {'closed_for_new_calls':True},{'prepaid_balance_usd':'NaN'},
                        {'prepaid_balance_usd':'Infinity'},{'prepaid_balance_usd':-1}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.make(**changes)
            self.value={**self.before,'screen_cap_usd':12,'prepaid_balance_usd':8,
                        'allocation_amendment':self.value['allocation_amendment']}
    def test_cap_parent_carry_and_total_cannot_change(self):
        for field,value in [('screen_cap_usd',13),('prior_spend_usd',0),
                            ('total_authorized_usd',999),('parent_ledger_sha256','changed')]:
            with self.subTest(field=field),self.assertRaises(ValueError):self.make(**{field:value})
            self.value={**self.before,'screen_cap_usd':12,'prepaid_balance_usd':8,
                        'allocation_amendment':self.value['allocation_amendment']}
    def test_ledger_corruption_and_exhaustion_rejected(self):
        original=self.ledger.read_bytes()
        for extra in (b'{"label":"retained-later","usd":"1"}\n',
                      b'{"label":"bad","usd":"NaN"}\n',b'{"label":"bad","usd":"-1"}\n',
                      b'{"label":"big","usd":"9"}\n',b'{"partial":'):
            self.ledger.write_bytes(original+extra)
            with self.subTest(extra=extra),self.assertRaises((ValueError,KeyError)):self.make()
        self.ledger.write_bytes(b'{"label":"replacement","usd":"1"}\n')
        with self.assertRaises(ValueError):self.make()
    def test_append_before_call_and_unknown_rows_still_count(self):
        gate=self.make();original=self.ledger.read_bytes();prices={'input':1,'output':1}
        gate.reserve('call1',3000000,0,prices);gate.reserve('call2',4000000,0,prices)
        self.assertTrue(self.ledger.read_bytes().startswith(original))
        self.assertEqual(gate._reserved(self.ledger.read_bytes()),Decimal('11.70'))
        with self.assertRaises(ValueError):gate.reserve('call3',1000000,0,prices)
        with self.assertRaises(ValueError):gate.reserve('call1',1,1,prices)
        self.assertEqual(len(self.ledger.read_text().splitlines()),4)
    def test_receipt_change_or_ledger_rollback_refuses_next_call(self):
        for kind in ('receipt','ledger'):
            with self.subTest(kind=kind):
                gate=self.make();original=self.ledger.read_bytes()
                gate.reserve('one',100,0,{'input':1,'output':1})
                if kind=='receipt':self.receipt.write_text(self.receipt.read_text()+' ')
                else:self.ledger.write_bytes(original)
                with self.assertRaises(ValueError):gate.reserve('two',100,0,{'input':1,'output':1})
                self.ledger.write_bytes(original)
    def test_negative_or_nonfinite_new_quotes_rejected(self):
        gate=self.make()
        for prompt,output,prices in [(-1,0,{'input':1,'output':1}),(1,0,{'input':'NaN','output':1})]:
            with self.subTest(prompt=prompt),self.assertRaises(ValueError):gate.reserve('bad',prompt,output,prices)

if __name__=='__main__':unittest.main()
