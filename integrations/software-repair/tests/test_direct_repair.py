import itertools
import json

import pytest

from repair_env.direct_environment import DirectRepairAction, DirectRepairEnvironment, DIRECT_TASK_IDS
from repair_env.environment import RepairAction, RepairEnvironment
from repair_env.tasks import SOURCE_PATH, make_task


def score(task_id, seed, content, direct):
    env = DirectRepairEnvironment() if direct else RepairEnvironment()
    env.reset(task_id=task_id, seed=seed)
    if direct:
        return env.step(DirectRepairAction(content=content)).reward
    env.step(RepairAction(op="write", path=SOURCE_PATH, content=content))
    return env.step(RepairAction(op="submit")).reward


@pytest.mark.parametrize("task_id", DIRECT_TASK_IDS)
@pytest.mark.parametrize("seed", [1110000, 1110100, 1110200, 1110300])
def test_same_oracle_cases_reward_and_constructed_repairs(task_id, seed):
    task = make_task(task_id, seed)
    edits = [
        ('required = set(base["order"] + base["blocked"])', 'required = set(base["order"])'),
        ('key = (cost, len(uncovered), len(selected), selected)',
         'key = (len(uncovered), cost, len(selected), selected)'),
        ('if cost < budget:', 'if cost <= budget:'),
        ('len(selected), selected[::-1])', 'len(selected), selected)'),
    ]
    candidates = [task.initial_source, "", "# comment\n" + task.initial_source,
                  task.reference_source, "import os\ndef f(): return os.environ"]
    # Every subset of the actual local edits: same baseline-normalized partial
    # semantics, without cherry-picking a subset that happens to get reward.
    active = [edit for edit in edits if edit[0] in task.initial_source]
    for count in range(1, len(active)):
        for chosen in itertools.combinations(active, count):
            text = task.initial_source
            for before, after in chosen:
                text = text.replace(before, after, 1)
            candidates.append(text)
    for source in candidates:
        assert score(task_id, seed, source, True) == score(task_id, seed, source, False)
    assert score(task_id, seed, task.reference_source, True) == 1
    assert score(task_id, seed, task.initial_source, True) == 0


def test_reset_is_deterministic_contains_full_source_examples_and_no_hidden_tests():
    a, b = DirectRepairEnvironment(), DirectRepairEnvironment()
    first = a.reset(task_id=DIRECT_TASK_IDS[-1], seed=1110400)
    second = b.reset(task_id=DIRECT_TASK_IDS[-1], seed=1110400)
    assert first.model_dump() == second.model_dump()
    assert first.source == a._task.initial_source
    assert first.examples and "Reply once" in first.prompt
    assert first.examples == b.reset(task_id=DIRECT_TASK_IDS[-1], seed=1110400).examples
    payload = json.dumps(first.model_dump())
    assert "reference_source" not in payload and "hidden" not in first.model_dump()
    # Hidden inputs are not copied into the example payload.
    from repair_env.tasks import compact_literal
    assert all(compact_literal((c.args, c.expected)) not in first.examples for c in a._task.hidden)


def test_one_action_terminal_state_reset_and_session_isolation():
    a, b = DirectRepairEnvironment(), DirectRepairEnvironment()
    a.reset(seed=1110500); b.reset(seed=1110501)
    result = a.step(DirectRepairAction(content=a._task.reference_source))
    assert result.done and result.reward == 1 and a.state.step_count == 1
    assert b.state.step_count == 0 and b._files[SOURCE_PATH] == b._task.initial_source
    assert a.step(DirectRepairAction(content="")).reward == 1
    a.reset(seed=1110502)
    assert a.state.step_count == 0 and a.step(DirectRepairAction(content="")).reward == 0


def test_only_declared_task_family_and_no_module_mutation_on_oversized_utf8():
    env = DirectRepairEnvironment()
    with pytest.raises(ValueError):
        env.reset(task_id="software_repair-clamp-d1", seed=1)
    env.reset(seed=1110600)
    original = env._files[SOURCE_PATH]
    result = env.step(DirectRepairAction(content="é" * 5000))
    assert result.done and result.error and result.reward == 0
    assert env._files[SOURCE_PATH] == original
    assert set(DirectRepairAction.model_json_schema()["required"]) == {"content"}
