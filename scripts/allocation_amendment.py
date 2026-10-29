"""Validate an explicit immutable allocation amendment; grant no new authority."""
from decimal import Decimal
import hashlib
import json
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verified_cap_ceiling(receipt, value, expected_authorization_sha256=None):
    if expected_authorization_sha256 is None:
        return Decimal(2)
    if len(expected_authorization_sha256) != 64:
        raise ValueError('explicit authorization digest required')
    amendment = value['allocation_amendment']
    auth_path = Path(amendment['authorization_receipt'])
    raw = auth_path.read_bytes()
    if digest(raw) != expected_authorization_sha256:
        raise ValueError('authorization changed')
    auth = json.loads(raw)
    if {k: v for k, v in amendment.items() if k != 'authorization_receipt'} != auth:
        raise ValueError('receipt amendment differs from authorized record')
    before_raw = (auth_path.parent/'receipt-before.json').read_bytes()
    prefix = (auth_path.parent/'ledger-before.jsonl').read_bytes()
    if (digest(before_raw) != auth['previous_receipt_sha256'] or
            digest(prefix) != auth['unchanged_ledger_sha256']):
        raise ValueError('amendment history changed')
    before = json.loads(before_raw)
    cap = Decimal(str(auth['new_cap_usd']))
    old = Decimal(str(auth['previous_cap_usd']))
    added = Decimal(str(auth['added_usd']))
    if (not all(x.is_finite() for x in (cap, old, added)) or
            added <= 0 or old <= 0 or cap != old+added or
            Decimal(str(before['screen_cap_usd'])) != old or
            Decimal(str(value['screen_cap_usd'])) != cap):
        raise ValueError('invalid authorized cap arithmetic')
    # Reconciliation may refresh billing fields; historical spending and
    # parent-chain/cumulative authorization fields may not be rewritten.
    for key in ('prior_spend_usd', 'total_authorized_usd',
                'parent_receipt', 'parent_ledger_sha256'):
        if value.get(key) != before.get(key):
            raise ValueError('protected cumulative/parent accounting changed')
    ledger = Path(receipt).with_suffix('.reservations.jsonl').read_bytes()
    if not ledger.startswith(prefix) or (prefix and not prefix.endswith(b'\n')):
        raise ValueError('existing reservations removed or rewritten')
    return cap
