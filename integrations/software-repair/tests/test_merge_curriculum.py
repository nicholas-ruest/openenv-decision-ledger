"""Constructed semantic witnesses, never model solves or learning evidence."""
import copy
import importlib.util
from pathlib import Path
import random

import pytest

from repair_env import hard_tasks, merge_curriculum
from repair_env.runner import Program
from repair_env.tasks import TRAINING_TASK_IDS, make_task

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("merge_audit", ROOT / "scripts/audit-software-curriculum.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


@pytest.mark.parametrize("seed", range(1076000, 1076008))
def test_diagnostic_preserves_contract_two_faults_and_pair_count_with_visible_witnesses(seed):
    old = make_task("software_repair-merge-d2", seed)
    new = make_task("software_repair-merge-d3", seed)
    assert Program(old.initial_source).fingerprint == Program(new.initial_source).fingerprint
    assert old.reference_source == new.reference_source and old.instructions == new.instructions
    assert new.task_id not in TRAINING_TASK_IDS
    assert all(len(case.args[0]) == 11 for case in old.public + old.hidden + new.public + new.hidden)
    row = audit.audit_instance(new)
    assert row["reference"]["public_passed"] == 6 and row["reference"]["hidden_passed"] == 30
    assert row["baseline"]["public_passed"] == 2 and row["baseline"]["hidden_passed"] == 10
    assert len(row["isolated_defects"]) == 2
    assert all(item["public_semantic_detection"] and item["hidden_semantic_activation"]
               and not item["hidden_active_public_missed"] for item in row["isolated_defects"])
    assert sorted(item["formula_reward"] for item in row["controlled_variants"]) == [.25, .5]
    assert all(not item["public_errors"] and not item["hidden_errors"] for item in row["controlled_variants"])


@pytest.mark.parametrize("mode", range(6))
def test_six_modes_keep_independent_semantic_failures_and_true_controls(mode):
    args = list(merge_curriculum.inputs(random.Random(1077000), 6))[mode]
    saved = copy.deepcopy(args)
    expected = hard_tasks.reference("merge", args)
    source = hard_tasks.SPECS["merge"][2]
    initial = hard_tasks.initial("merge", source, 2)
    nested = initial.replace("result[-1][1] = pair[1]", "result[-1][1] = max(result[-1][1], pair[1])")
    touching = initial.replace("or pair[0] == result[-1][1]", "or merge_touching and pair[0] == result[-1][1]")
    assert (Program(initial).run("merge_ranges", args) == expected) == (mode in (3, 4))
    assert (Program(nested).run("merge_ranges", args) == expected) == (mode in (0, 3, 4, 5))
    assert (Program(touching).run("merge_ranges", args) == expected) == (mode in (1, 3, 4))
    assert Program(source).run("merge_ranges", args) == expected
    assert args == saved  # Neither the trusted oracle nor interpreter mutates nested inputs.


def test_fresh_cohort_has_no_reused_inputs_split_overlap_or_fake_seed_diversity():
    tasks = [make_task("software_repair-merge-d3", seed) for seed in range(1078000, 1078016)]
    measured = audit.cohort_diversity(tasks)
    assert measured["case_occurrences"] == measured["distinct_input_keys"] == 16 * 36
    assert measured["seed_independent_content_suites"] == 16
    assert not measured["public_hidden_overlap_input_keys"] and not measured["conflicting_expected_label_keys"]
    assert TRAINING_TASK_IDS == [f"software_repair-{family}-d{level}"
                                for family in ("plan", "cover", "merge", "replay") for level in (1, 2)]


@pytest.mark.parametrize("fix,expected", [("nested", .5), ("touching", .25), ("both", 1)])
def test_diagnostic_native_rewards_match_constructed_control_without_changing_export(fix, expected):
    pytest.importorskip("openenv")
    from repair_env.environment import RepairAction, RepairEnvironment
    env = RepairEnvironment()
    task = make_task("software_repair-merge-d3", 1079000)
    env.reset(task_id=task.task_id, seed=task.seed)
    source = task.initial_source
    if fix in ("nested", "both"):
        source = source.replace("result[-1][1] = pair[1]", "result[-1][1] = max(result[-1][1], pair[1])")
    if fix in ("touching", "both"):
        source = source.replace("or pair[0] == result[-1][1]", "or merge_touching and pair[0] == result[-1][1]")
    assert not env.step(RepairAction(op="write", path="src/solution.py", content=source)).error
    assert env.step(RepairAction(op="submit")).reward == expected
    spec = importlib.util.spec_from_file_location("merge_export", ROOT / "integrations/software-repair/scripts/export_dataset.py")
    export = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(export)
    request = export.request("ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:" + "0" * 64)
    assert [item["task_id"] for item in request["tasks"]] == TRAINING_TASK_IDS
    assert task.task_id not in [item["task_id"] for item in request["tasks"]]
