"""Observation-only policy tests; no credentials, model calls or grading change."""
import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('policy', ROOT / 'scripts/software-helper-policy.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class Observation(SimpleNamespace):
    def model_copy(self, deep=False):
        return copy.deepcopy(self)


@pytest.mark.parametrize('task', p.TASK_TARGETS)
def test_only_prompt_changes_and_original_is_untouched(task):
    original = Observation(task_id=task, prompt='contract', source='code', examples='cases', reward=0, done=False)
    baseline = p.transform(original, 'baseline')
    changed = p.transform(original, 'preserve_supplied')
    assert vars(baseline) == vars(original) and baseline is not original
    assert changed.prompt == 'contract' + p.guidance(task)
    changed.prompt = original.prompt
    assert vars(changed) == vars(original)


def test_wrapper_routes_real_reset_and_restores_on_error():
    class Env:
        def reset(self, task_id):
            return Observation(task_id=task_id, prompt='contract')
        def step(self, action):
            return action
    base = SimpleNamespace(DirectRepairEnvironment=Env)
    with pytest.raises(RuntimeError):
        with p.environment_policy(base, 'preserve_supplied'):
            env = base.DirectRepairEnvironment()
            assert env.reset(next(iter(p.TASK_TARGETS))).prompt.startswith('contract\nRepair focus:')
            assert env.step('unchanged grading') == 'unchanged grading'
            raise RuntimeError('injected worker failure')
    assert base.DirectRepairEnvironment is Env


@pytest.mark.parametrize('arm', ['unknown', None, True])
def test_unknown_arm_rejected(arm):
    with pytest.raises(ValueError):
        p.transform(Observation(task_id=next(iter(p.TASK_TARGETS))), arm)


def test_joint_task_is_not_silently_reclassified():
    with pytest.raises(ValueError):
        p.transform(Observation(task_id='software_repair-ignore-d2'), 'baseline')


def test_protocol_seeds_are_disjoint_from_old_screen_and_each_other():
    assert not set(p.SEEDS['screen']) & set(p.SEEDS['confirmation'])
    assert not set(sum(p.SEEDS.values(), ())) & {2180000, 2180100, 2190000, 2190100}
