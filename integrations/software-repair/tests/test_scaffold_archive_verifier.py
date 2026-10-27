"""Reject tampered raw evidence before accepting a calibration result."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import copy
import pytest
ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('verifier', ROOT / 'scripts/verify-software-scaffold-archive.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def fixture():
    saved = [{'task_id': t, 'seed': s} for t in ('d3', 'd4') for s in (1, 2)]
    raw = [{'task_id': 'd3', 'seed': 1, 'failure': 'provider', 'calls': [
        {'client_call_label': 'call', 'reserved_usd': .02}]}]
    runner = SimpleNamespace(TASKS=('d3', 'd4'), SEEDS=(1, 2),
        capture=lambda base, t, s: {'task_id': t, 'seed': s}, digest=lambda _: 'hash',
        normalize=lambda row, snapshot, sha: copy.deepcopy(row))
    assessor = SimpleNamespace(TASKS=('d2', 'd3', 'd4'), assess=lambda *args:
                              {'groups': [{'task_id': 'd3', 'seed': 1}]})
    return [raw, copy.deepcopy(raw), saved, {'settings': {}, 'provider': {}},
            runner, None, assessor, [{'label': 'call', 'usd': '.02'}]]


def test_matching_archive():
    r = v.attest(*fixture())
    assert r['reservation_identity_match'] and not r['confirmed'] and not r['is_training']
    assert r['raw_failures'] == {'provider': 1}


@pytest.mark.parametrize('tamper', ['reset', 'missing_reset', 'record', 'reservation', 'duplicate'])
def test_tampering_rejected(tamper):
    args = fixture()
    if tamper == 'reset': args[2][0]['seed'] = 3
    if tamper == 'missing_reset': args[2].pop()
    if tamper == 'record': args[1][0]['failure'] = None
    if tamper == 'reservation': args[7][0]['usd'] = '.01'
    if tamper == 'duplicate': args[7].append(dict(args[7][0]))
    with pytest.raises(ValueError): v.attest(*args)


def test_restore_only_supplied_functions_and_keep_model_target():
    before = 'def helper(x): return x+1\ndef target(x): return False'
    model = 'def helper(x): return x-1\ndef target(x): return helper(x)'
    changed, restored = v.restore_supplied(before, model, 'target')
    assert changed == ['helper']
    namespace = {}; exec(restored, namespace)
    assert namespace['target'](2) == 3


def test_missing_supplied_function_restored():
    changed, restored = v.restore_supplied('def helper(): return 1\ndef target(): return 0',
                                         'def target(): return helper()', 'target')
    namespace = {}; exec(restored, namespace)
    assert changed == ['helper'] and namespace['target']() == 1
