import pytest

from repair_env.tasks import make_task
from repair_env.environment import check, RepairAction, RepairEnvironment
from repair_env.direct_environment import DirectRepairEnvironment, DirectRepairAction
from repair_env.runner import Program
from repair_env import release_plan


@pytest.mark.parametrize("seed", [1117000, 1117100, 1117200, 1117300])
def test_synthesis_changes_source_not_cases_or_oracle_and_has_semantic_gradient(seed):
    old = make_task("software_repair-release-d3", seed)
    task = make_task("software_repair-release-d4", seed)
    assert old.public == task.public and old.hidden == task.hidden
    assert old.reference_source == task.reference_source
    assert old.initial_source != task.initial_source
    for cases in (task.public, task.hidden):
        _, before = check(Program(task.initial_source), task, cases, details=True)
        _, after = check(Program(task.reference_source), task, cases, details=True)
        assert all(row["error"] is None for row in before + after)
        assert any(not row["passed"] for row in before)
        assert all(row["passed"] for row in after)
    # Implements the graph helper but omits cycle reporting. This is a genuine
    # executable wrong repair; cyclic cases distinguish it from the reference.
    partial = task.reference_source.replace('"cycles": sorted(cycles)', '"cycles": []')
    env = DirectRepairEnvironment(); env.reset(task_id=task.task_id, seed=seed)
    assert env.step(DirectRepairAction(content=task.initial_source)).reward == 0
    env.reset(task_id=task.task_id, seed=seed)
    result = env.step(DirectRepairAction(content=partial))
    assert 0 < result.reward < 1
    env.reset(task_id=task.task_id, seed=seed)
    assert env.step(DirectRepairAction(content=task.reference_source)).reward == 1


def test_timeout_extension_is_bounded_and_legacy_profiles_remain_180_seconds():
    import importlib.util
    from pathlib import Path
    p = Path(__file__).parents[1] / "scripts/screen_profiles.py"
    spec = importlib.util.spec_from_file_location("synthesis_profiles", p)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    old = module.get_profile("direct_release", "screen")
    profile = module.get_profile("direct_synthesis", "screen")
    assert old["sampling_settings"]["request_timeout_seconds"] == 180
    assert profile["sampling_settings"]["request_timeout_seconds"] == 360
    assert profile["sampling_settings"]["stage_wall_seconds"] == 1200
    assert profile["max_calls"] == 8 and profile["required_productive_groups"] == 2
    assert profile["signal_task_ids"] == ["software_repair-release-d4"]
    confirm = module.get_profile("direct_synthesis", "confirm")
    assert set(map(tuple, profile["groups"])).isdisjoint(map(tuple, confirm["groups"]))
    control = module.get_profile("direct_capacity_control", "screen")
    assert control["sampling_settings"] == profile["sampling_settings"]
    assert [seed for task, seed in control["groups"]] == [seed for task, seed in profile["groups"]]
