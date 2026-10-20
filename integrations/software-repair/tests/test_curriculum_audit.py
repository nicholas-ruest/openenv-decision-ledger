"""Check the audit against the real reward path, without a provider or model."""

import importlib.util
from pathlib import Path

import pytest

from repair_env.tasks import make_task

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("curriculum_audit", ROOT / "scripts/audit-software-curriculum.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_replay_partial_edits_are_semantic_and_do_not_raise_execution_errors():
    task = make_task("software_repair-replay-d2", 1050000)
    row = audit.audit_instance(task)
    assert row["local_edit_count"] == 2
    assert row["reference"]["hidden_passed"] == 30
    assert len(row["controlled_variants"]) == 2
    for item in row["controlled_variants"]:
        assert not item["public_errors"] and not item["hidden_errors"]
        assert item["formula_reward"] == 0


def test_partial_control_can_receive_actual_fractional_reward():
    row = audit.audit_instance(make_task("software_repair-release-d1", 1050000))
    assert any(0 < item["formula_reward"] < 1 for item in row["controlled_variants"])
    assert not row["counts_as_model_rollout"]


@pytest.mark.parametrize("value,other", [([True], [1]), ((1,), [1]), ({"x": False}, {"x": 0})])
def test_type_differences_are_not_silently_counted_as_oracle_agreement(value, other):
    assert not audit.exact(value, other)


@pytest.mark.parametrize("task_id", ["software_repair-cover-d1", "software_repair-merge-d2",
                                    "software_repair-replay-d2", "software_repair-release-d1"])
def test_audit_reward_formula_agrees_with_native_environment(task_id):
    pytest.importorskip("openenv")
    from repair_env.environment import RepairAction, RepairEnvironment

    task = make_task(task_id, 1050000)
    row = audit.audit_instance(task)
    _, variants = audit.controls(task)
    for (_, _, source), measured in zip(variants, row["controlled_variants"]):
        env = RepairEnvironment()
        env.reset(task_id=task_id, seed=task.seed)
        assert not env.step(RepairAction(op="write", path="src/solution.py", content=source)).error
        assert env.step(RepairAction(op="submit")).reward == measured["formula_reward"]
