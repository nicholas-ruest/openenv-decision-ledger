"""Offline re-attestation of an existing probe; no inference, retries or submission."""
import argparse
import ast
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import statistics
import importlib.util

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def read_rows(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x]


def restore_supplied(initial, candidate, target):
    """Posthoc diagnostic only: restore supplied functions, preserving model target."""
    before = {n.name: n for n in ast.parse(initial).body if isinstance(n, ast.FunctionDef)}
    tree = ast.parse(candidate)
    after = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    changed = sorted(n for n in before if n != target and
                     (n not in after or ast.dump(before[n]) != ast.dump(after[n])))
    tree.body = [before[n.name] if isinstance(n, ast.FunctionDef) and n.name in changed else n
                 for n in tree.body]
    tree.body.extend(before[n] for n in changed if n not in after)
    return changed, ast.unparse(ast.fix_missing_locations(tree))


def attest(raw, normalized, saved, protocol, runner, base, assessor, reservations):
    """Compare records against fresh native resets and actual saved requests/replies."""
    expected = {(t, s) for t in runner.TASKS for s in runner.SEEDS}
    snapshots = {(r['task_id'], r['seed']): r for r in saved}
    if len(saved) != 4 or set(snapshots) != expected:
        raise ValueError('complete reset archive required')
    for key, old in snapshots.items():
        if runner.capture(base, *key) != old:
            raise ValueError('fresh frozen native reset/cases differ from archive')
    settings_sha = runner.digest({'settings': protocol['settings'], 'provider': protocol['provider']})
    rebuilt = []
    ledger = {}
    for r in reservations:
        label = r.get('label')
        if label in ledger:
            raise ValueError('duplicate reservation identity')
        ledger[label] = r
    for row in raw:
        exp = snapshots[(row['task_id'], row['seed'])]
        record = runner.normalize(row, exp, settings_sha)
        for call in row['calls']:
            reserved = ledger.get(call['client_call_label'])
            if reserved is None or Decimal(str(reserved['usd'])) != Decimal(str(call['reserved_usd'])):
                raise ValueError('observed call lacks matching append-before-call reservation')
        rebuilt.append(record)
    if rebuilt != normalized:
        raise ValueError('normalized records differ from actual raw requests/replies')
    result = assessor.assess(rebuilt, 'screen', assessor.TASKS[1:])
    partials, component_audits = [], []
    for row in raw:
        if row['failure'] is not None:
            continue
        env = base.DirectRepairEnvironment()
        env.reset(task_id=row['task_id'], seed=row['seed'])
        action = json.loads(row['messages'][2]['content'])
        if set(action) == {'action'}:
            action = action['action']
        obs = env.step(base.DirectRepairAction.model_validate(action))
        if not obs.done or obs.error or float(obs.reward) != row['reward']:
            raise ValueError('saved model action does not reproduce actual live reward')
        _, outcomes = base.check(base.Program(env._files[base.SOURCE_PATH]), env._task, env._task.hidden, details=True)
        errors = sum(o['error'] is not None for o in outcomes)
        wrong = sum(not o['passed'] and o['error'] is None for o in outcomes)
        if errors != row['hidden_execution_rejections'] or wrong != row['hidden_wrong_answers']:
            raise ValueError('saved hidden failure diagnosis does not reproduce')
        target = 'classify_ignore' if row['task_id'].endswith('d3') else 'rule_mode'
        changed, restored = restore_supplied(snapshots[row['task_id'], row['seed']]['files']['src/solution.py'],
                                            env._files[base.SOURCE_PATH], target)
        entry = {'task_id': row['task_id'], 'seed': row['seed'], 'sample': row['sample'],
                 'live_reward': row['reward'], 'changed_supplied_functions': changed}
        if changed:
            diagnostic = base.DirectRepairEnvironment()
            diagnostic.reset(task_id=row['task_id'], seed=row['seed'])
            restored_obs = diagnostic.step(base.DirectRepairAction(content=restored))
            entry.update(posthoc_restored_reward=float(restored_obs.reward),
                         posthoc_restored_error=restored_obs.error)
        component_audits.append(entry)
        if row['reward'] < 1:
            partials.append({'task_id': row['task_id'], 'seed': row['seed'], 'sample': row['sample'],
                            'reward': row['reward'], 'wrong_answers': wrong, 'execution_errors': errors,
                            'mismatches': [o for o in outcomes if not o['passed']]})
    groups = []
    for g in result['groups']:
        rewards = [r['reward'] for r in rebuilt if (r['task_id'], r['seed']) == (g['task_id'], g['seed']) and r['failure'] is None]
        groups.append({**g, 'rewards': rewards, 'population_std': statistics.pstdev(rewards) if rewards else None})
    return {'groups': groups, 'rollouts': len(raw), 'prompt_groups': 4, 'underlying_procedural_cases': 2,
            'raw_failures': dict(Counter(r['failure'] for r in raw if r['failure'] is not None)),
            'fresh_native_resets_match': True, 'raw_prompt_and_normalized_records_match': True,
            'independent_call_and_response_identities': True, 'reservation_identity_match': True,
            'all_saved_valid_actions_reward_replayed': True, 'partial_diagnosis': partials,
            'component_preservation': component_audits,
            'settings_sha256': settings_sha, 'joint_model_baseline': False,
            'confirmed': False, 'is_training': False, 'model_improvement_claim': False,
            'checkpoint_attested': False, 'thinking_attested': False, 'arena_wrapper_equivalent': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--runtime-root', type=Path, required=True)
    p.add_argument('--ledger', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError('preserve earlier attestations; fresh output required')
    runner = load('archive_runner', ROOT / 'scripts/run-software-scaffold-probe.py')
    for name, sha in json.loads((ROOT / 'config/software-probe-source-hashes-20261027.json').read_text()).items():
        if hashlib.sha256((a.runtime_root / name).read_bytes()).hexdigest() != sha:
            raise ValueError('frozen source changed')
    base = load('archive_base', a.runtime_root / 'scripts/repair-signal-screen.py')
    assessor = load('archive_assessor', ROOT / 'scripts/assess-software-stage-comparison.py')
    r = a.archive
    report = attest(read_rows(r / 'raw-episodes.jsonl'), read_rows(r / 'records.jsonl'),
                    json.loads((r / 'resets.json').read_text()), json.loads((r / 'protocol.json').read_text()),
                    runner, base, assessor, read_rows(a.ledger))
    report['archive_sha256'] = {n: hashlib.sha256((r / n).read_bytes()).hexdigest() for n in
                               ('raw-episodes.jsonl', 'records.jsonl', 'resets.json', 'protocol.json', 'complete.json')}
    a.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
