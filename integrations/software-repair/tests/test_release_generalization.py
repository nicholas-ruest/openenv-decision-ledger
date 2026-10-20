import copy
import itertools
import json

import pytest

from repair_env import release_plan
from repair_env.environment import RepairAction, RepairEnvironment, check
from repair_env.runner import Program
from repair_env.tasks import TRAINING_TASK_IDS, make_task, task_fingerprint


READINESS = ' and all([dep not in pending or dep in order for dep in graph[name]])'
REPAIRS = [
    ('required = set(base["order"] + base["blocked"])', 'required = set(base["order"])'),
    ('key = (cost, len(uncovered),', 'key = (len(uncovered), cost,'),
    ('if cost < budget:', 'if cost <= budget:'),
    ('len(selected), selected[::-1])', 'len(selected), selected)'),
]


def test_old_release_d2_cases_and_default_mix_are_preserved():
    assert task_fingerprint(make_task('software_repair-release-d2', 1093000)) == 'c9f38496b95426e2164d6c08e4c28f14b167b565e27e9eb8c0f9bb42f0cbb47e'
    assert 'software_repair-release-d3' not in TRAINING_TASK_IDS


@pytest.mark.parametrize('seed', [1099000, 1099001, 1099002, 1099003])
def test_reference_independent_oracle_and_full_python_agree_without_aliasing(seed):
    task = make_task('software_repair-release-d3', seed)
    assert task_fingerprint(task) == task_fingerprint(make_task(task.task_id, seed))
    namespace = {}
    exec(task.reference_source, namespace, namespace)  # Trusted static fixture only.
    program = Program(task.reference_source)
    for case in task.public + task.hidden:
        before = copy.deepcopy(case.args)
        assert release_plan.reference(case.args) == case.expected
        assert namespace[task.entrypoint](*copy.deepcopy(case.args)) == case.expected
        assert program.run(task.entrypoint, case.args) == case.expected
        assert case.args == before
    public = {json.dumps(case.args, sort_keys=True) for case in task.public}
    hidden = {json.dumps(case.args, sort_keys=True) for case in task.hidden}
    assert len(public) == 6 and len(hidden) == 30 and public.isdisjoint(hidden)


@pytest.mark.parametrize('seed', [1099000, 1099001, 1099002, 1099003])
def test_new_examples_and_hidden_cases_reject_ignored_dependency_readiness(seed):
    source = release_plan.REFERENCE.replace(READINESS, '')
    assert source != release_plan.REFERENCE
    program = Program(source)
    prior = make_task('software_repair-release-d2', seed)
    assert check(program, prior, prior.public)[0] == 6
    assert check(program, prior, prior.hidden)[0] == 30
    task = make_task('software_repair-release-d3', seed)
    for cases in (task.public, task.hidden):
        passed, details = check(program, task, cases, details=True)
        assert passed < len(cases)
        assert all(item['error'] is None for item in details)


@pytest.mark.parametrize('seed', [1099000, 1099001, 1099002, 1099003])
def test_all_proper_seeded_repair_subsets_retain_native_partial_reward(seed):
    task = make_task('software_repair-release-d3', seed)
    selected = [(old, new) for old, new in REPAIRS if old in task.initial_source]
    assert len(selected) == 3
    for size in (1, 2):
        for subset in itertools.combinations(selected, size):
            source = task.initial_source
            for old, new in subset:
                assert source.count(old) == 1
                source = source.replace(old, new)
            _, details = check(Program(source), task, task.hidden, details=True)
            assert all(item['error'] is None for item in details)
            env = RepairEnvironment()
            env.reset(task_id=task.task_id, seed=seed)
            env.step(RepairAction(op='write', path='src/solution.py', content=source))
            result = env.step(RepairAction(op='submit'))
            assert result.done and 0 < result.reward < 1
