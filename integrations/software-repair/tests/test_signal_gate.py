import importlib.util
import hashlib
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("signal_gate", Path(__file__).parents[1] / "scripts/analyze_screen.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def fixture(rewards, failures=None, seed=1, stage="screen", task="task"):
    failures = failures or [None] * len(rewards)
    protocol = {"groups": [[task, seed]], "samples_per_group": 4, "stage": stage,
                "provider": {"id": "fixed"}, "source_files_sha256": {"file": "fixed"}, "tokenizer_sha256": "fixed",
                "planned_confirmation_groups": [[task, seed+1]]}
    rows = [{"task_id": task, "seed": seed, "sample": i, "reward": reward,
             "solved": reward == 1, "failure": failure,
             "prompt_sha256": hashlib.sha256(f"prompt:{task}:{seed}".encode()).hexdigest(),
             "hidden_execution_rejections": 0, "hidden_wrong_answers": int(reward != 1),
             "calls": [{"client_call_label": f"sample:{task}:{seed}:{i}",
                        "provider_response_id_sha256": hashlib.sha256(f"reply:{task}:{seed}:{i}".encode()).hexdigest()}]}
            for i, (reward, failure) in enumerate(zip(rewards, failures))]
    return protocol, rows


def test_failures_cannot_manufacture_productive_variance():
    protocol, rows = fixture([1, 1, 0, 0], [None, None, "provider_timeout", "budget"])
    result = gate.classify(protocol, rows)
    assert not result["genuine_signal_screened"]
    assert result["groups"][0]["valid_rewards"] == [1, 1]
    assert result["groups"][0]["wrong"] == 0


def test_actual_valid_partial_and_wrong_answers_supply_signal():
    protocol, rows = fixture([1, .8, 0, 1])
    result = gate.classify(protocol, rows)
    assert result["genuine_signal_screened"]
    assert result["groups"][0]["partial"] == 1 and result["groups"][0]["wrong"] == 1


@pytest.mark.parametrize("defect", ["duplicate", "identity", "missing_diagnostic"])
def test_bad_identity_or_missing_diagnostics_fail_closed(defect):
    protocol, rows = fixture([1, .8, 0, 1])
    if defect == "duplicate":
        rows[-1]["sample"] = 0
    elif defect == "identity":
        rows[-1]["prompt_sha256"] = "b" * 64
    else:
        rows[-1].pop("hidden_wrong_answers")
    with pytest.raises(ValueError):
        gate.classify(protocol, rows)


def test_incomplete_and_saturated_groups_do_not_qualify():
    protocol, rows = fixture([1, .8, 0])
    assert not gate.classify(protocol, rows)["genuine_signal_screened"]
    protocol, rows = fixture([1, 1, 1, 1])
    assert not gate.classify(protocol, rows)["genuine_signal_screened"]


@pytest.mark.parametrize("field", ["client_call_label", "provider_response_id_sha256"])
def test_reused_request_or_response_identity_cannot_supply_independent_signal(field):
    protocol, rows = fixture([1, .8, 0, 1])
    for index, row in enumerate(rows):
        row["calls"] = [{"client_call_label": "call-" + str(index),
                         "provider_response_id_sha256": format(index, "064x")}]
    assert gate.classify(protocol, rows)["genuine_signal_screened"]
    rows[-1]["calls"][0][field] = rows[0]["calls"][0][field]
    assert not gate.classify(protocol, rows)["genuine_signal_screened"]


def test_confirmation_needs_fresh_matched_productive_prompts_and_never_authorizes_submission():
    p, rows = fixture([1, .8, 0, 1])
    q, fresh = fixture([1, 1, .9, 1], seed=2, stage="confirm")
    result = gate.confirmation(p, gate.classify(p, rows), q, gate.classify(q, fresh))
    assert result["provisional_single_family_signal_confirmed"]
    assert not result["is_model_improvement"] and not result["arena_submission_authorized"]
    q["provider"] = {"id": "changed"}
    with pytest.raises(ValueError):
        gate.confirmation(p, gate.classify(p, rows), q, gate.classify(q, fresh))


@pytest.mark.parametrize("missing", ["calls", "client_call_label", "provider_response_id_sha256"])
def test_missing_call_identity_cannot_supply_signal(missing):
    protocol, rows = fixture([1, .8, 0, 1])
    if missing == "calls":
        rows[-1].pop("calls")
    else:
        rows[-1]["calls"][0].pop(missing)
    result = gate.classify(protocol, rows)
    assert result["groups"][0]["productive"]
    assert not result["genuine_signal_screened"]
    assert not result["sampling_identity_verified"]


@pytest.mark.parametrize("bad_id", [None, 123, "", "z" * 64, "a" * 63])
def test_malformed_response_identity_cannot_supply_signal(bad_id):
    protocol, rows = fixture([1, .8, 0, 1])
    rows[0]["calls"][0]["provider_response_id_sha256"] = bad_id
    assert not gate.classify(protocol, rows)["genuine_signal_screened"]


@pytest.mark.parametrize("field", ["client_call_label", "provider_response_id_sha256"])
def test_confirmation_rejects_response_or_request_reuse_across_stages(field):
    p, rows = fixture([1, .8, 0, 1])
    q, fresh = fixture([1, 1, .9, 1], seed=2, stage="confirm")
    fresh[-1]["calls"][0][field] = rows[0]["calls"][0][field]
    screen, confirmed = gate.classify(p, rows), gate.classify(q, fresh)
    assert screen["genuine_signal_screened"] and confirmed["genuine_signal_screened"]
    result = gate.confirmation(p, screen, q, confirmed)
    assert not result["sampling_identities_disjoint"]
    assert not result["provisional_single_family_signal_confirmed"]


def test_legacy_missing_id_archives_remain_descriptive_only():
    p, rows = fixture([1, .8, 0, 1])
    for row in rows:
        row.pop("calls")
    result = gate.classify(p, rows)
    assert result["groups"][0]["valid_rewards"] == [1, .8, 0, 1]
    assert not result["genuine_signal_screened"]


@pytest.mark.parametrize("field,value", [
    ("hidden_wrong_answers", -1), ("hidden_wrong_answers", 1),
    ("hidden_execution_rejections", False), ("solved", 1),
])
def test_inconsistent_completed_grader_diagnostics_are_rejected(field, value):
    p, rows = fixture([1, .8, 0, 1])
    rows[0][field] = value
    with pytest.raises(ValueError, match="consistent grader"):
        gate.classify(p, rows)


def mixed(old, candidate, seed=1, stage="screen"):
    p, baseline = fixture(old, seed=seed, stage=stage, task="old")
    q, diagnostic = fixture(candidate, seed=seed, stage=stage, task="candidate")
    p["groups"] += q["groups"]
    p["planned_confirmation_groups"] += q["planned_confirmation_groups"]
    p.update(profile="comparison", signal_task_ids=["candidate"], sampling_settings={"temperature": .7})
    return p, baseline + diagnostic


@pytest.mark.parametrize("screen_candidate,confirm_candidate,expected", [
    ([1, 1, 1, 1], [1, 1, 1, 1], False),
    ([1, 1, 1, 1], [1, .5, 0, 1], False),
    ([1, .5, 0, 1], [1, 1, 1, 1], False),
    ([1, .5, 0, 1], [1, .5, 0, 1], True),
])
def test_old_arm_signal_cannot_confirm_candidate(screen_candidate, confirm_candidate, expected):
    p, rows = mixed([1, .5, 0, 1], screen_candidate)
    q, fresh = mixed([1, .5, 0, 1], confirm_candidate, seed=2, stage="confirm")
    result = gate.confirmation(p, gate.classify(p, rows), q, gate.classify(q, fresh))
    assert result["tasks"]["old"]["confirmed"]
    assert result["provisional_single_family_signal_confirmed"] is expected
    assert result["tasks"]["candidate"]["confirmed"] is expected
    assert result["signal_task_ids"] == ["candidate"]
    assert not result["is_model_improvement"] and not result["arena_submission_authorized"]


def test_other_arm_provider_failure_does_not_fabricate_or_erase_candidate_signal():
    p, rows = mixed([0] * 4, [1, .5, 0, 1])
    q, fresh = mixed([0] * 4, [1, .5, 0, 1], seed=2, stage="confirm")
    for group in (rows, fresh):
        for row in group[:4]:
            row["failure"] = "provider_timeout"
            row["calls"] = []
    before, after = gate.classify(p, rows), gate.classify(q, fresh)
    assert not before["tasks"]["old"]["sampling_identity_verified"]
    assert before["tasks"]["candidate"]["sampling_identity_verified"]
    result = gate.confirmation(p, before, q, after)
    assert result["provisional_single_family_signal_confirmed"]
    assert not result["tasks"]["old"]["confirmed"]


def test_mixed_legacy_archive_without_declared_candidate_remains_descriptive():
    p, rows = mixed([1, .5, 0, 1], [1, .5, 0, 1])
    p.pop("signal_task_ids")
    result = gate.classify(p, rows)
    assert all(t["genuine_signal_screened"] for t in result["tasks"].values())
    assert not result["genuine_signal_screened"]


@pytest.mark.parametrize("targets", [[], ["missing"], ["candidate", "candidate"], "candidate"])
def test_invalid_signal_targets_fail_closed(targets):
    p, rows = mixed([1, .5, 0, 1], [1, .5, 0, 1])
    p["signal_task_ids"] = targets
    with pytest.raises(ValueError, match="signal tasks"):
        gate.classify(p, rows)


@pytest.mark.parametrize("field", ["client_call_label", "provider_response_id_sha256"])
def test_cross_arm_identity_reuse_within_or_across_stages_cannot_confirm(field):
    p, rows = mixed([1, .5, 0, 1], [1, .5, 0, 1])
    q, fresh = mixed([1, .5, 0, 1], [1, .5, 0, 1], seed=2, stage="confirm")
    fresh[-1]["calls"][0][field] = rows[0]["calls"][0][field]
    result = gate.confirmation(p, gate.classify(p, rows), q, gate.classify(q, fresh))
    assert not result["provisional_single_family_signal_confirmed"]
    rows[-1]["calls"][0][field] = rows[0]["calls"][0][field]
    assert not gate.classify(p, rows)["genuine_signal_screened"]


def test_new_seed_with_reused_prompt_is_not_fresh_confirmation():
    p, rows = fixture([1, .5, 0, 1])
    q, fresh = fixture([1, .5, 0, 1], seed=2, stage="confirm")
    for row in fresh:
        row["prompt_sha256"] = rows[0]["prompt_sha256"]
    before, after = gate.classify(p, rows), gate.classify(q, fresh)
    assert before["genuine_signal_screened"] and after["genuine_signal_screened"]
    result = gate.confirmation(p, before, q, after)
    assert not result["tasks"]["task"]["prompt_identities_disjoint"]
    assert not result["provisional_single_family_signal_confirmed"]


def test_distinct_planned_groups_cannot_count_one_prompt_twice():
    p, rows = mixed([1, .5, 0, 1], [1, .5, 0, 1])
    for row in rows[4:]:
        row["prompt_sha256"] = rows[0]["prompt_sha256"]
    with pytest.raises(ValueError, match="reuse a prompt"):
        gate.classify(p, rows)


def test_changed_sampling_settings_or_legacy_gate_cannot_confirm():
    p, rows = mixed([1, .5, 0, 1], [1, .5, 0, 1])
    q, fresh = mixed([1, .5, 0, 1], [1, .5, 0, 1], seed=2, stage="confirm")
    before, after = gate.classify(p, rows), gate.classify(q, fresh)
    q["sampling_settings"]["temperature"] = 0
    with pytest.raises(ValueError, match="unmatched"):
        gate.confirmation(p, before, q, after)
    q["sampling_settings"]["temperature"] = .7
    before["signal_gate_version"] = after["signal_gate_version"] = 2
    assert not gate.confirmation(p, before, q, after)["provisional_single_family_signal_confirmed"]
