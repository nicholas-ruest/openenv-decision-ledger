"""Process-local software observation policy; no model calls or publication."""
import argparse
from contextlib import contextmanager
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

TASK_TARGETS = {'software_repair-ignore-d3': 'classify_ignore',
                'software_repair-ignore-d4': 'rule_mode'}
ARMS = ('baseline', 'preserve_supplied')
SEEDS = {'screen': (2200000, 2200100), 'confirmation': (2210000, 2210100)}


def guidance(task_id):
    target = TASK_TARGETS[task_id]
    return ('\nRepair focus: implement the missing ' + target + ' function. '
            'The other supplied functions are complete reusable components. '
            'Prefer preserving them and calling them as documented; change one '
            'only if needed to satisfy the stated contract. Return the complete '
            'module, including all supplied functions. This guidance does not '
            'change the contract or scoring, and alternate correct implementations '
            'remain valid.')


def transform(observation, arm):
    if arm not in ARMS:
        raise ValueError('explicit frozen arm required')
    if observation.task_id not in TASK_TARGETS:
        raise ValueError('software prerequisite tasks only')
    result = observation.model_copy(deep=True)
    if arm == 'preserve_supplied':
        result.prompt += guidance(result.task_id)
    return result


@contextmanager
def environment_policy(base, arm):
    """Use in an isolated, single-arm process before capture AND episode calls.

    Never switch arms while a worker is active. No shared module/runtime edit.
    """
    if arm not in ARMS:
        raise ValueError('explicit frozen arm required')
    original = base.DirectRepairEnvironment

    class PolicyEnvironment(original):
        def reset(self, *args, **kwargs):
            return transform(super().reset(*args, **kwargs), arm)

    base.DirectRepairEnvironment = PolicyEnvironment
    try:
        yield
    finally:
        base.DirectRepairEnvironment = original


def build_plan(base, runner, phase):
    if phase not in SEEDS:
        raise ValueError('screen or confirmation required')
    captured = {}
    for arm in ARMS:
        with environment_policy(base, arm):
            captured[arm] = [runner.capture(base, task, seed) for task in TASK_TARGETS
                             for seed in SEEDS[phase]]
    groups = []
    for baseline, variant in zip(captured['baseline'], captured['preserve_supplied']):
        # Only observation.prompt may change. All grading/workspace/example data
        # must match exactly, with independent arm-specific request identities.
        restored = copy.deepcopy(variant['reset'])
        suffix = guidance(variant['task_id'])
        if not restored['prompt'].endswith(suffix):
            raise ValueError('guidance suffix missing')
        restored['prompt'] = restored['prompt'][:-len(suffix)]
        if restored != baseline['reset']:
            raise ValueError('policy changed reset data beyond instructions')
        for field in ('files', 'case_sha256', 'workspace_sha256'):
            if variant[field] != baseline[field]:
                raise ValueError('policy changed cases/workspace')
        if variant['prompt_sha256'] == baseline['prompt_sha256']:
            raise ValueError('distinct arm instructions required')
        groups.append({'task_id': baseline['task_id'], 'seed': baseline['seed'],
                       'case_sha256': baseline['case_sha256'],
                       'workspace_sha256': baseline['workspace_sha256'],
                       'arms': {arm: {'prompt_sha256': captured[arm][len(groups)]['prompt_sha256'],
                                     'prompt_bound': captured[arm][len(groups)]['prompt_bound'],
                                     'reset_sha256': captured[arm][len(groups)]['reset_sha256']}
                                for arm in ARMS}})
    return {'phase': phase, 'arms': ARMS, 'groups': groups, 'calls_required': 32,
            'samples_per_arm_group': 4, 'unique_procedural_cases': 2,
            'model_calls_performed': 0, 'executed': False,
            'comparison_unit': 'prompt group; sampled attempts are not unique cases',
            'selection': 'all samples and all failure classes; no survivor-only effect estimate',
            'execution_requirements': ['independent single-arm process and fresh archive per arm',
                'identical provider/settings/runtime; arm-specific prompt identities',
                'fresh billing reconciliation and whole-phase existing-cap admission',
                'raw actual prompt/workspace/call/response identity verification',
                'new disjoint confirmation; no reuse of earlier screen as baseline'],
            'not_arena_runtime': True, 'model_improvement_claim': False}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.output.exists():
        raise ValueError('preserve existing manifest; fresh output required')
    for path, sha in json.loads((root / 'config/software-probe-source-hashes-20261027.json').read_text()).items():
        if hashlib.sha256((args.runtime_root / path).read_bytes()).hexdigest() != sha:
            raise ValueError('frozen runtime/helper dependency changed')
    base = load('helper_policy_base', args.runtime_root / 'scripts/repair-signal-screen.py')
    runner = load('helper_policy_runner', root / 'scripts/run-software-scaffold-probe.py')
    plans = {phase: build_plan(base, runner, phase) for phase in SEEDS}
    if ({g['case_sha256'] for g in plans['screen']['groups']} &
            {g['case_sha256'] for g in plans['confirmation']['groups']}):
        raise ValueError('confirmation procedural case leakage')
    if set(SEEDS['screen']) & set(SEEDS['confirmation']):
        raise ValueError('confirmation seed leakage')
    args.output.write_text(json.dumps(plans, indent=2) + '\n')
    print(json.dumps({'offline_manifests': 2, 'phase_calls_required': 32, 'paid_calls': 0}))


if __name__ == '__main__':
    main()
