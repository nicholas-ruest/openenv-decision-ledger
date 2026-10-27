"""Synthetic evidence corruption and denominator tests, not model results."""
import copy
import importlib.util
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('pair', ROOT / 'scripts/assess-software-helper-pair.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
SETTINGS = p.digest('settings')


def fixture(phase='screen'):
    manifest = {'phase': phase, 'arms': list(p.ARMS), 'groups': []}
    rows = []
    for task in p.TASKS:
        for seed in p.SEEDS[phase]:
            group = {'task_id': task, 'seed': seed, 'case_sha256': p.digest(seed),
                     'workspace_sha256': p.digest((task, seed)), 'arms': {}}
            for arm in p.ARMS:
                ids = {f: p.digest((phase, task, seed, arm, f)) for f in ('reset_sha256', 'prompt_sha256')}
                group['arms'][arm] = ids
                for n in range(4):
                    rows.append({'arm': arm, 'task_id': task, 'seed': seed, 'sample': n,
                        'case_sha256': group['case_sha256'], 'workspace_sha256': group['workspace_sha256'],
                        **ids, 'runtime_source': p.RUNTIME, 'settings_sha256': SETTINGS,
                        'client_call_label': str((phase, task, seed, arm, n)),
                        'provider_response_id_sha256': p.digest((phase, task, seed, arm, n)),
                        'provider_call_observed': True, 'reward': 1 if arm == p.ARMS[1] else .75,
                        'failure': None})
            manifest['groups'].append(group)
    return manifest, rows


def run(m, rows):
    return p.assess(m, rows, p.RUNTIME, SETTINGS)


def test_known_effect_and_no_promotion():
    result = run(*fixture())
    assert result['mean_prompt_group_full_rate_difference'] == 1
    assert result['rollouts'] == 32 and result['underlying_cases'] == 2
    assert result['raw_evidence_attestation_required'] and not result['promotion']


def test_failures_stay_in_denominator_and_out_of_semantic_wrong():
    m, rows = fixture()
    r = next(r for r in rows if r['arm'] == p.ARMS[1])
    r.update(failure='budget', reward=0, provider_call_observed=False, provider_response_id_sha256=None)
    result = run(m, rows)
    group = result['groups'][0]
    assert group['arms'][p.ARMS[1]]['wrong'] == 0
    assert group['arms'][p.ARMS[1]]['valid'] == 3
    assert group['arms'][p.ARMS[1]]['failures'] == {'budget': 1}
    assert group['full_rate_difference_all_attempts'] == .75


@pytest.mark.parametrize('damage', ['missing', 'duplicate', 'settings', 'source', 'prompt', 'workspace',
    'case', 'reset', 'response', 'call', 'bool_sample', 'nan', 'unobserved', 'unknown_failure'])
def test_invalid_evidence_rejected(damage):
    m, rows = fixture()
    r = rows[-1]
    if damage == 'missing': rows.pop()
    if damage == 'duplicate': rows[-1] = copy.deepcopy(rows[0])
    if damage == 'settings': r['settings_sha256'] = p.digest('wrong settings')
    if damage == 'source': r['runtime_source'] = 'wrong'
    for key, field in [('prompt', 'prompt_sha256'), ('workspace', 'workspace_sha256'),
                       ('case', 'case_sha256'), ('reset', 'reset_sha256')]:
        if damage == key: r[field] = p.digest('different')
    if damage == 'response': r['provider_response_id_sha256'] = rows[0]['provider_response_id_sha256']
    if damage == 'call': r['client_call_label'] = rows[0]['client_call_label']
    if damage == 'bool_sample': r['sample'] = True
    if damage == 'nan': r['reward'] = float('nan')
    if damage == 'unobserved': r['provider_call_observed'] = False
    if damage == 'unknown_failure': r['failure'] = 'whatever'
    with pytest.raises(ValueError): run(m, rows)


def test_confirmation_recomputed_from_records():
    sm, sr = fixture()
    cm, cr = fixture('confirmation')
    result = p.confirm(sm, sr, cm, cr, p.RUNTIME, SETTINGS)
    assert result['positive_full_rate_direction_in_both'] and not result['promotion']
    sr.pop()
    with pytest.raises(ValueError): p.confirm(sm, sr, cm, cr, p.RUNTIME, SETTINGS)


@pytest.mark.parametrize('field', ['case', 'call', 'response'])
def test_confirmation_leakage_rejected(field):
    sm, sr = fixture()
    cm, cr = fixture('confirmation')
    if field == 'case':
        source = sm['groups'][0]['case_sha256']
        old = cm['groups'][0]['case_sha256']
        for g in cm['groups']:
            if g['case_sha256'] == old: g['case_sha256'] = source
        for r in cr:
            if r['case_sha256'] == old: r['case_sha256'] = source
    if field == 'call': cr[0]['client_call_label'] = sr[0]['client_call_label']
    if field == 'response': cr[0]['provider_response_id_sha256'] = sr[0]['provider_response_id_sha256']
    with pytest.raises(ValueError): p.confirm(sm, sr, cm, cr, p.RUNTIME, SETTINGS)
