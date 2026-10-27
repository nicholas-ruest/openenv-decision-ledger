import copy
import json

import pytest

from repair_env import release_plan
from repair_env.environment import RepairAction, RepairEnvironment, check
from repair_env.runner import Program
from repair_env.tasks import TRAINING_TASK_IDS, make_task


def result(order, tests, cost, uncovered=(), blocked=(), cycles=(), unknown=()):
    return {"affected": sorted(list(order) + list(blocked)), "order": list(order),
            "blocked": list(blocked), "cycles": list(cycles), "unknown": list(unknown),
            "tests": list(tests), "test_cost": cost, "uncovered": list(uncovered)}


@pytest.mark.parametrize("args,expected", [
    ([{"a": [], "b": ["a"]}, ["a"],
      {"z": {"targets": ["a", "b"], "cost": 4},
       "a": {"targets": ["a"], "cost": 1},
       "b": {"targets": ["b"], "cost": 1}}, 4], result(["a", "b"], ["a", "b"], 2)),
    ([{"a": []}, ["a"], {"free": {"targets": ["a"], "cost": 0}}, 0],
     result(["a"], ["free"], 0)),
    ([{"a": []}, ["a"], {"paid": {"targets": ["a"], "cost": 2}}, 1],
     result(["a"], [], 0, ["a"])),
    ([{"a": [], "b": [], "c": []}, ["a", "b", "c"],
      {"alpha": {"targets": ["a"], "cost": 2},
       "beta": {"targets": ["b"], "cost": 1},
       "gamma": {"targets": ["c"], "cost": 1}}, 2],
     result(["a", "b", "c"], ["beta", "gamma"], 2, ["a"])),
    ([{"a": ["a"], "b": ["a"], "c": []}, ["a", "c"],
      {"irrelevant": {"targets": ["a", "b"], "cost": 0},
       "actual": {"targets": ["c"], "cost": 2}}, 2],
     result(["c"], ["actual"], 2, blocked=["a", "b"], cycles=[["a"]])),
    ([{"a": []}, ["missing", "missing"],
      {"free": {"targets": ["a"], "cost": 0}}, 0],
     result([], [], 0, unknown=["missing"])),
    ([{"x": [], "y": [], "z": []}, ["x", "y", "z"],
      {"a": {"targets": ["x"], "cost": 1},
       "z": {"targets": ["y", "z"], "cost": 1},
       "b": {"targets": ["x", "y"], "cost": 1},
       "c": {"targets": ["z"], "cost": 1}}, 2],
     result(["x", "y", "z"], ["a", "z"], 2)),
])
def test_release_contract_with_independent_handwritten_expectations(args, expected):
    before = copy.deepcopy(args)
    assert release_plan.reference(args) == expected
    assert Program(release_plan.REFERENCE).run("plan_release", args) == expected
    assert args == before


@pytest.mark.parametrize("seed", range(1010000, 1010008))
def test_seeded_release_mutants_are_valid_and_reference_repair_is_complete(seed):
    task = make_task("software_repair-release-d1", seed)
    passed, rows = check(Program(task.initial_source), task, task.hidden, details=True)
    assert 0 < passed < len(task.hidden)
    assert all(row["error"] is None for row in rows)
    assert check(Program(task.reference_source), task, task.public + task.hidden)[0] == 36
    public = {json.dumps(case.args, sort_keys=True) for case in task.public}
    hidden = {json.dumps(case.args, sort_keys=True) for case in task.hidden}
    assert public.isdisjoint(hidden) and len(hidden) == 30
    assert task == make_task(task.task_id, seed)
    assert task.task_id not in TRAINING_TASK_IDS


def test_release_uses_the_real_patch_test_submit_workflow():
    env = RepairEnvironment()
    env.reset(task_id="software_repair-release-d1", seed=1010100)
    initial = env._files["src/solution.py"]
    assert env.step(RepairAction(op="submit")).reward == 0
    env.reset(task_id="software_repair-release-d1", seed=1010100)
    assert not env.step(RepairAction(op="patch", path="src/solution.py",
                                    search=initial, replacement=env._task.reference_source)).error
    assert json.loads(env.step(RepairAction(op="test")).content)["passed"] == 6
    assert env.step(RepairAction(op="submit")).reward == 1


@pytest.mark.parametrize("seed", [1010000, 1010100])
def test_incomplete_semantic_release_repair_earns_partial_credit(seed):
    env = RepairEnvironment()
    env.reset(task_id="software_repair-release-d1", seed=seed)
    result = env.step(RepairAction(
        op="patch", path="src/solution.py",
        search='required = set(base["order"] + base["blocked"])',
        replacement='required = set(base["order"])'))
    assert not result.error
    assert 0 < env.step(RepairAction(op="submit")).reward < 1
