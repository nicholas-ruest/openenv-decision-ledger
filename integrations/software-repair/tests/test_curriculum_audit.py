"""Check the audit against the real reward path, without a provider or model."""

import importlib.util
from dataclasses import replace
from pathlib import Path

import pytest

from repair_env.tasks import Case, make_task, task_fingerprint

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


@pytest.mark.parametrize("value,other", [([True], [1]), ((1,), [1]), ({"x": False}, {"x": 0})])
def test_content_identity_keeps_grader_relevant_types(value, other):
    assert audit.fingerprint(audit.typed_value(value)) != audit.fingerprint(audit.typed_value(other))


def test_input_mapping_order_preserved_but_expected_mapping_order_ignored():
    a, b = {"x": 1, "y": 2}, {"y": 2, "x": 1}
    assert audit.typed_value(a) != audit.typed_value(b)
    assert audit.typed_value(a, input_order=False) == audit.typed_value(b, input_order=False)
    with pytest.raises(TypeError, match="identity type"):
        audit.typed_value(object())


def test_seed_and_comment_changes_do_not_fake_case_diversity():
    task = make_task("software_repair-replay-d3", 1073000)
    clone = replace(task, seed=task.seed + 1, initial_source="# different case label\n" + task.initial_source)
    assert task_fingerprint(task) != task_fingerprint(clone)
    result = audit.cohort_diversity([task, clone])
    assert result["case_occurrences"] == 72 and result["distinct_input_keys"] == 36
    assert result["cross_seed_duplicate_input_keys"] == 36
    assert result["seed_independent_content_suites"] == 1
    assert len(result["duplicated_content_suites"]) == 1
    assert result["public_hidden_overlap_input_keys"] == result["conflicting_expected_label_keys"] == 0


def test_actual_cross_seed_split_overlap_and_conflicting_labels_are_reported():
    task = make_task("software_repair-replay-d3", 1073000)
    other = replace(task, seed=task.seed + 1, public=(task.hidden[0],), hidden=())
    result = audit.cohort_diversity([task, other])
    assert result["public_hidden_overlap_input_keys"] == 1
    conflict = replace(other, public=(Case(task.hidden[0].args, {"wrong": True}),))
    result = audit.cohort_diversity([task, conflict])
    assert result["conflicting_expected_label_keys"] == 1
    assert result["conflicting_label_owners"]


def test_isolated_mutants_detect_each_replay_fault_without_execution_failures():
    task = make_task("software_repair-replay-d3", 1073000)
    defects = audit.isolated_defects(task, audit.edits(task))
    assert {item["defect"] for item in defects} == {"undo", "duplicate_guard"}
    assert all(item["public_semantic_detection"] and item["hidden_semantic_activation"] for item in defects)
    assert all(not item["public_errors"] and not item["hidden_errors"] for item in defects)
    assert not any(item["hidden_active_public_missed"] for item in defects)
    assert audit.isolated_defects(make_task("software_repair-plan-d2", 1073000), []) == []


@pytest.mark.parametrize("seed", [1074000, 1074001, 1074005])
def test_d4_isolation_uses_unique_original_sites_not_ambiguous_correct_loop_text(seed):
    task = make_task("software_repair-plan-d4", seed)
    local = audit.edits(task)
    defects = audit.isolated_defects(task, local)
    assert len(defects) == len(local) >= 3
    assert all(not item["public_errors"] and not item["hidden_errors"] for item in defects)


def test_real_public_detection_blind_spot_is_not_hidden_by_compound_failure():
    task = make_task("software_repair-replay-d3", 1073000)
    # A case the undo-defective/duplicate-correct program passes; hidden cases
    # still activate undo. Only the visible fixture changes in this test.
    duplicate_only = task.initial_source.replace("if True:", "if identifier not in seen:")
    program = audit.Program(duplicate_only)
    quiet = next(case for case in task.public if audit.exact(program.run(task.entrypoint, case.args), case.expected))
    probe = replace(task, public=(quiet,))
    defects = audit.isolated_defects(probe, audit.edits(probe))
    undo = next(item for item in defects if item["defect"] == "undo")
    assert undo["hidden_active_public_missed"] and not undo["public_semantic_detection"]
    assert undo["hidden_semantic_activation"]


def test_read_byte_proxies_match_native_content_not_envelope_or_tokens():
    pytest.importorskip("openenv")
    from repair_env.environment import RepairAction, RepairEnvironment
    task = make_task("software_repair-replay-d3", 1073000)
    row = audit.audit_instance(task)
    env = RepairEnvironment()
    env.reset(task_id=task.task_id, seed=task.seed)
    sizes = row["read_content_utf8_bytes"]
    assert len(env.step(RepairAction(op="read", path="*")).content.encode()) == sizes["all"]
    assert len(env.step(RepairAction(op="read", path="src/solution.py")).content.encode()) == sizes["source"]
    assert len(env.step(RepairAction(op="read", path="tests/test_public.py#case=1")).content.encode()) == sizes["individual_public_cases"][0]


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
