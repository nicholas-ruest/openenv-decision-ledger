"""Offline paired calibration assessment. No network, training or promotion."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import statistics

RUNTIME = '0b8ccc3ca70a67fed5fc5837b69022261cc60497'
ARMS = ('baseline', 'preserve_supplied')
TASKS = ('software_repair-ignore-d3', 'software_repair-ignore-d4')
SEEDS = {'screen': (2200000, 2200100), 'confirmation': (2210000, 2210100)}
FAILURES = {'format', 'provider', 'truncation', 'execution', 'budget'}


def sha(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('complete SHA256 identity required')
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def assess(manifest, rows, runtime_source, settings_sha256):
    if runtime_source != RUNTIME:
        raise ValueError('frozen runtime required')
    sha(settings_sha256)
    phase = manifest['phase']
    if phase not in SEEDS or tuple(manifest['arms']) != ARMS:
        raise ValueError('declared phase and both arms required')
    expected_groups = {(t, s) for t in TASKS for s in SEEDS[phase]}
    groups = {}
    case_by_seed = {}
    prompts = set()
    for group in manifest['groups']:
        if type(group['seed']) is not int:
            raise ValueError('integer seed required')
        key = (group['task_id'], group['seed'])
        if key not in expected_groups or key in groups or set(group['arms']) != set(ARMS):
            raise ValueError('duplicate or unexpected manifest group')
        case = sha(group['case_sha256'])
        if group['seed'] in case_by_seed and case_by_seed[group['seed']] != case:
            raise ValueError('matched tasks require same procedural case')
        case_by_seed[group['seed']] = case
        sha(group['workspace_sha256'])
        for arm in ARMS:
            prompt = sha(group['arms'][arm]['prompt_sha256'])
            sha(group['arms'][arm]['reset_sha256'])
            if prompt in prompts:
                raise ValueError('distinct group/arm prompts required')
            prompts.add(prompt)
        groups[key] = group
    if set(groups) != expected_groups or len(set(case_by_seed.values())) != 2:
        raise ValueError('complete distinct procedural cases required')
    expected = {(a, t, s, n) for a in ARMS for t, s in groups for n in range(4)}
    seen, calls, responses, buckets = set(), set(), set(), {}
    for row in rows:
        if type(row['seed']) is not int or type(row['sample']) is not int:
            raise ValueError('integer sample identity required')
        key = (row['arm'], row['task_id'], row['seed'], row['sample'])
        if key not in expected or key in seen:
            raise ValueError('duplicate/unexpected sample')
        seen.add(key)
        if row['runtime_source'] != runtime_source or row['settings_sha256'] != settings_sha256:
            raise ValueError('runtime/settings mismatch')
        g = groups[key[1:3]]
        identities = {k: g[k] for k in ('case_sha256', 'workspace_sha256')}
        identities.update({k: g['arms'][row['arm']][k] for k in ('prompt_sha256', 'reset_sha256')})
        if any(row[k] != v for k, v in identities.items()):
            raise ValueError('actual evidence differs from frozen arm manifest')
        label = row['client_call_label']
        if not isinstance(label, str) or not label or label in calls:
            raise ValueError('independent call labels required')
        calls.add(label)
        response = row.get('provider_response_id_sha256')
        observed = row.get('provider_call_observed')
        if type(observed) is not bool:
            raise ValueError('explicit observed-call status required')
        if response is not None:
            sha(response)
            if not observed or response in responses:
                raise ValueError('unobserved or duplicated provider response')
            responses.add(response)
        failure = row['failure']
        if failure is None:
            reward = row['reward']
            if not observed or response is None:
                raise ValueError('valid completion needs actual independent response')
            if type(reward) not in (int, float) or not math.isfinite(reward) or not 0 <= reward <= 1:
                raise ValueError('finite semantic reward required')
        elif failure not in FAILURES:
            raise ValueError('unknown failure must not be counted as wrong')
        buckets.setdefault(key[:3], []).append(row)
    if seen != expected:
        raise ValueError('incomplete phase; no survivor-only result')
    summaries, differences = [], []
    for task, seed in sorted(groups):
        arms = {}
        for arm in ARMS:
            values = buckets[(arm, task, seed)]
            valid = [r['reward'] for r in values if r['failure'] is None]
            arms[arm] = {'attempted': 4, 'valid': len(valid),
                'full': sum(v == 1 for v in valid), 'partial': sum(0 < v < 1 for v in valid),
                'wrong': sum(v == 0 for v in valid),
                'failures': dict(Counter(r['failure'] for r in values if r['failure'])),
                'valid_mean_reward': statistics.mean(valid) if valid else None,
                'valid_population_std': statistics.pstdev(valid) if valid else None}
        delta = (arms[ARMS[1]]['full'] - arms[ARMS[0]]['full']) / 4
        differences.append(delta)
        summaries.append({'task_id': task, 'seed': seed, 'arms': arms,
                          'full_rate_difference_all_attempts': delta})
    return {'phase': phase, 'groups': summaries, 'rollouts': 32, 'underlying_cases': 2,
            'mean_prompt_group_full_rate_difference': statistics.mean(differences),
            'settings_sha256': settings_sha256, 'case_ids': sorted(set(case_by_seed.values())),
            'prompt_ids': sorted(prompts), 'call_ids': sorted(calls), 'response_ids': sorted(responses),
            'manifest_sha256': digest(manifest), 'records_sha256': digest(rows),
            'raw_evidence_attestation_required': True, 'is_training': False, 'promotion': False,
            'model_improvement_claim': False}


def confirm(screen_manifest, screen_rows, confirmation_manifest, confirmation_rows, runtime_source, settings_sha256):
    if screen_manifest['phase'] != 'screen' or confirmation_manifest['phase'] != 'confirmation':
        raise ValueError('screen then confirmation required')
    first = assess(screen_manifest, screen_rows, runtime_source, settings_sha256)
    second = assess(confirmation_manifest, confirmation_rows, runtime_source, settings_sha256)
    for field in ('case_ids', 'prompt_ids', 'call_ids', 'response_ids'):
        if set(first[field]) & set(second[field]):
            raise ValueError('screen/confirmation evidence leakage')
    return {'screen': first, 'confirmation': second,
            'positive_full_rate_direction_in_both': all(r['mean_prompt_group_full_rate_difference'] > 0
                                                       for r in (first, second)),
            'statistical_significance_claim': False, 'trained_policy_gain_claim': False,
            'promotion': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--records', type=Path, required=True)
    p.add_argument('--settings-sha256', required=True)
    p.add_argument('--runtime-source', required=True)
    a = p.parse_args()
    print(json.dumps(assess(json.loads(a.manifest.read_text()),
        [json.loads(r) for r in a.records.read_text().splitlines() if r],
        a.runtime_source, a.settings_sha256), indent=2))
