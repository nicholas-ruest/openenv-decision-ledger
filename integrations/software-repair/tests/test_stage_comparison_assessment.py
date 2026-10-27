"""Synthetic assessor fixtures verify rejection rules, never model results."""
import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("stage_comparison", ROOT / "scripts/assess-software-stage-comparison.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def h(value):
    return hashlib.sha256(str(value).encode()).hexdigest()


def records(phase="screen"):
    return [{"task_id": task, "seed": seed, "sample": sample,
             "runtime_source": MODULE.RUNTIME, "settings_sha256": h("settings"),
             "case_sha256": h(seed), "prompt_sha256": h((task, seed, "prompt")),
             "reset_sha256": h((task, seed, "reset")),
             "workspace_sha256": h((task, seed, "workspace")),
             "client_call_label": str((task, seed, sample)),
             "provider_response_id_sha256": h((task, seed, sample)),
             "failure": None, "reward": [1, .75, 1, 0][sample]}
            for task in MODULE.TASKS for seed in MODULE.SEEDS[phase] for sample in range(4)]


def test_matched_independent_groups_and_fresh_confirmation():
    a = MODULE.assess(records(), "screen")
    b = MODULE.assess(records("confirmation"), "confirmation")
    assert len(a["groups"]) == 6
    assert MODULE.confirm(records(), records("confirmation"))["independently_productive_tasks"] == sorted(MODULE.TASKS)
    assert not MODULE.confirm(records(), records("confirmation"))["promotion"]


@pytest.mark.parametrize("field,value", [("failure", "unknown"), ("reward", float("nan")),
    ("reward", True), ("runtime_source", "wrong"), ("settings_sha256", h("other")),
    ("workspace_sha256", h("other")), ("case_sha256", h("other")), ("sample", True)])
def test_corruption_rejected(field, value):
    rows = records()
    rows[0][field] = value
    with pytest.raises(ValueError):
        MODULE.assess(rows, "screen")


def test_replayed_response_and_duplicate_row_rejected():
    rows = records()
    rows[1]["provider_response_id_sha256"] = rows[0]["provider_response_id_sha256"]
    with pytest.raises(ValueError):
        MODULE.assess(rows, "screen")
    with pytest.raises(ValueError):
        MODULE.assess(records() + [records()[0]], "screen")


def test_failures_are_not_wrong_and_no_partial_group_selection():
    rows = records()
    rows[0].update(failure="provider", reward=None)
    result = MODULE.assess(rows, "screen")
    group = next(g for g in result["groups"] if g["task_id"] == rows[0]["task_id"] and g["seed"] == rows[0]["seed"])
    assert group["valid"] == 3 and group["wrong"] == 1
    assert group["failures"] == {"provider": 1} and not group["productive"]


def test_confirmation_settings_and_identity_leakage_rejected():
    a, b = records(), records("confirmation")
    # Copy an actual response identity, preserving all other matched fields.
    b[0]["provider_response_id_sha256"] = a[0]["provider_response_id_sha256"]
    with pytest.raises(ValueError):
        MODULE.confirm(a, b)


def test_smaller_declared_protocol_never_counts_missing_joint_as_productive():
    rows = [r for r in records() if r["task_id"] in MODULE.TASKS[1:]]
    with pytest.raises(ValueError):
        MODULE.assess(rows, "screen")
    value = MODULE.assess(rows, "screen", MODULE.TASKS[1:])
    assert len(value["groups"]) == 4 and not value["joint_model_baseline"]
    assert MODULE.TASKS[0] not in value["provisional_productive_tasks"]
