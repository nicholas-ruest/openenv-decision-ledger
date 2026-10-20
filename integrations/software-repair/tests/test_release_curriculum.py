import copy
import json

import pytest

from repair_env import release_plan
from repair_env.environment import RepairAction, RepairEnvironment, check
from repair_env.runner import Program
from repair_env.tasks import TRAINING_TASK_IDS, make_task


FAULTS = (
    ('required = set(base["order"])', 'required = set(base["order"] + base["blocked"])'),
    ('key = (len(uncovered), cost,', 'key = (cost, len(uncovered),'),
    ('if cost <= budget:', 'if cost < budget:'),
    ('len(selected), selected)', 'len(selected), selected[::-1])'),
)


@pytest.mark.parametrize("seed", range(1090000, 1090008))
def test_public_cases_expose_each_semantic_fault_without_interpreter_failures(seed):
    task = make_task("software_repair-release-d2", seed)
    # Each isolated public mode detects its corresponding single mutant.
    for index, (good, bad) in enumerate(FAULTS):
        mutant = Program(task.reference_source.replace(good, bad))
        _, rows = check(mutant, task, task.public, details=True)
        assert all(row["error"] is None for row in rows)
        assert not rows[index]["passed"]
        # The other three isolated witnesses remain correct.
        assert all(rows[other]["passed"] for other in range(4) if other != index)


@pytest.mark.parametrize("seed", range(1090100, 1090108))
def test_every_single_fix_of_a_seeded_defect_earns_genuine_partial_reward(seed):
    task = make_task("software_repair-release-d2", seed)
    assert task == make_task(task.task_id, seed)
    defects = [(good, bad) for good, bad in FAULTS if bad in task.initial_source]
    assert len(defects) == 3
    public = {json.dumps(case.args, sort_keys=True) for case in task.public}
    hidden = {json.dumps(case.args, sort_keys=True) for case in task.hidden}
    assert len(hidden) == 30 and public.isdisjoint(hidden)
    assert check(Program(task.reference_source), task, task.public + task.hidden)[0] == 36
    for good, bad in defects:
        env = RepairEnvironment()
        env.reset(task_id=task.task_id, seed=seed)
        env.step(RepairAction(op="write", path="src/solution.py",
                             content=task.initial_source.replace(bad, good)))
        result = env.step(RepairAction(op="submit"))
        assert result.done and 0 < result.reward < 1
        _, rows = check(Program(env._files["src/solution.py"]), task, task.hidden, details=True)
        assert all(row["error"] is None for row in rows)
    assert task.task_id not in TRAINING_TASK_IDS


def test_new_cases_retain_independent_oracle_and_no_input_mutation():
    task = make_task("software_repair-release-d2", 1090200)
    namespace = {}
    exec(task.reference_source, {}, namespace)  # Trusted static fixture only.
    for case in task.public + task.hidden:
        before = copy.deepcopy(case.args)
        assert release_plan.reference(case.args) == case.expected
        assert namespace[task.entrypoint](*copy.deepcopy(case.args)) == case.expected
        assert case.args == before
