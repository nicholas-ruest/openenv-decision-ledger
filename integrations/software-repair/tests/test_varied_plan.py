import hashlib
import json

import pytest

from repair_env.environment import RepairAction, RepairEnvironment, check
from repair_env.runner import Program
from repair_env.tasks import TRAINING_TASK_IDS, make_task, task_fingerprint


@pytest.mark.parametrize("seed", range(1000000, 1000024))
def test_varied_planner_defects_are_semantic_and_independently_repairable(seed):
    task = make_task("software_repair-plan-d4", seed)
    before, results = check(Program(task.initial_source), task, task.hidden, details=True)
    assert 0 < before < len(task.hidden)
    assert all(case["error"] is None for case in results)
    fixed = Program(task.reference_source)
    assert check(fixed, task, task.public)[0] == len(task.public)
    assert check(fixed, task, task.hidden)[0] == len(task.hidden)
    public = {json.dumps(case.args, sort_keys=True) for case in task.public}
    hidden = {json.dumps(case.args, sort_keys=True) for case in task.hidden}
    assert public.isdisjoint(hidden)
    assert len(hidden) == 30
    assert task == make_task(task.task_id, seed)


def test_defect_sources_vary_without_changing_the_contract_or_training_mix():
    tasks = [make_task("software_repair-plan-d4", seed) for seed in range(1000000, 1000024)]
    # Exclude the case-ID comment: code itself must vary across seeds.
    fingerprints = {hashlib.sha256(task.initial_source.split("\n", 1)[1].encode()).hexdigest()
                    for task in tasks}
    assert len(fingerprints) >= 8
    assert len({task.reference_source for task in tasks}) == 1
    assert len({task.instructions for task in tasks}) == 1
    assert "software_repair-plan-d4" not in TRAINING_TASK_IDS


@pytest.mark.parametrize("seed,expected", [
    (995000, "9932e677cb4dabbb8a0ac3b8971685768938c83367a06fb5456cf694709dbf23"),
    (995100, "9517a77c9f9cf7c42835c355a9cb75617a1ebcc8035ece7846d8ac0de6b72b43"),
])
def test_previous_measured_d3_instances_remain_identical(seed, expected):
    assert task_fingerprint(make_task("software_repair-plan-d3", seed)) == expected


def test_varied_planner_obeys_the_real_edit_submit_workflow():
    env = RepairEnvironment()
    env.reset(task_id="software_repair-plan-d4", seed=1000200)
    source = env._files["src/solution.py"]
    assert env.step(RepairAction(op="submit")).reward == 0
    env.reset(task_id="software_repair-plan-d4", seed=1000200)
    result = env.step(RepairAction(op="patch", path="src/solution.py", search=source,
                                   replacement=env._task.reference_source))
    assert not result.error
    assert env.step(RepairAction(op="submit")).reward == 1
