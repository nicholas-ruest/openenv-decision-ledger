import importlib.util
import hashlib
import json
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


def test_failed_finish_diagnostics_never_supply_valid_reward_variance():
    protocol, rows = fixture([1, 1, 0, 0], [None, None, "invalid_json_action", "episode_budget_exceeded"])
    for row, reward in zip(rows[2:], [.5, .75]):
        row["termination_grading"] = {"available": True, "terminal_reward": reward,
                                       "counts_as_valid_completion": False}
    result = gate.classify(protocol, rows)
    assert not result["genuine_signal_screened"]
    assert result["groups"][0]["valid_rewards"] == [1, 1]
    assert result["groups"][0]["partial"] == result["groups"][0]["wrong"] == 0


def test_actual_valid_partial_and_wrong_answers_supply_signal():
    protocol, rows = fixture([1, .8, 0, 1])
    result = gate.classify(protocol, rows)
    assert result["genuine_signal_screened"]
    assert result["groups"][0]["partial"] == 1 and result["groups"][0]["wrong"] == 1


def test_two_reliability_samples_cannot_pass_the_training_signal_gate():
    protocol, rows = fixture([1, .5])
    protocol.update(samples_per_group=2, purpose="reliability_only")
    result = gate.classify(protocol, rows)
    assert result["complete"] and result["groups"][0]["valid"] == 2
    assert not result["groups"][0]["productive"]
    assert not result["genuine_signal_screened"]


def test_internal_failure_without_observed_prompt_is_descriptive_not_signal():
    protocol, rows = fixture([1, .5, 1, 0], [None, None, None, "screen_internal_failure"])
    rows[-1].pop("prompt_sha256")
    rows[-1].update(prompt_identity_unavailable=True, calls=[])
    result = gate.classify(protocol, rows)
    group = result["groups"][0]
    assert group["productive"] and group["valid_rewards"] == [1, .5, 1]
    assert group["failures"] == {"screen_internal_failure": 1}
    assert group["prompt_identity_unavailable_samples"] == 1
    assert not group["prompt_identity_verified"]
    assert not result["sampling_identity_verified"] and not result["genuine_signal_screened"]
    rows[-1]["failure"] = None
    with pytest.raises(ValueError):
        gate.classify(protocol, rows)


def test_all_internal_failures_are_analyzable_without_fabricated_prompt_ids(tmp_path):
    task = "software_repair-replay-d3"
    protocol = {"groups": [[task, 1071000]], "samples_per_group": 4,
                "stage": "screen", "source_files_sha256": {}}
    rows = [{"task_id": task, "seed": 1071000, "sample": i,
             "failure": "screen_internal_failure", "reward": 0, "solved": False,
             "calls": [], "prompt_identity_unavailable": True} for i in range(4)]
    (tmp_path / "protocol.json").write_text(json.dumps(protocol))
    (tmp_path / "complete.json").write_text("{}")
    archive = tmp_path / "episodes.jsonl"
    archive.write_text("\n".join(json.dumps(row) for row in rows))
    _, result = gate.load_verified(tmp_path)
    assert result["complete"] and result["distinct_observed_prompts"] == 0
    assert result["groups"][0]["valid"] == 0
    assert result["groups"][0]["failures"] == {"screen_internal_failure": 4}
    assert not result["genuine_signal_screened"]
    rows[0]["messages"] = [{"content": "fabricated"}]
    archive.write_text("\n".join(json.dumps(row) for row in rows))
    with pytest.raises(ValueError, match="conflicts"):
        gate.load_verified(tmp_path)
    rows[0].pop("messages")
    rows[0].pop("prompt_identity_unavailable")
    archive.write_text("\n".join(json.dumps(row) for row in rows))
    with pytest.raises(ValueError, match="explicit failure marker"):
        gate.load_verified(tmp_path)


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


def worker_events():
    return [{"event": "starting", "wall_seconds": 1}, {"event": "started", "pid": 123},
            {"event": "terminal", "pid": 123, "status": "completed", "worker_exitcode": 0,
             "shutdown_verified": True, "finished_before_deadline": True}]


@pytest.mark.parametrize("field,value", [("status", "timed_out"), ("shutdown_verified", False),
    ("finished_before_deadline", False), ("worker_exitcode", 1), ("pid", 124)])
def test_complete_marker_cannot_override_failed_worker_receipt(tmp_path, field, value):
    root = tmp_path / "run"
    root.mkdir()
    protocol = {"worker_supervision": {"required": True, "wall_seconds": 1}}
    (root / "complete.json").write_text("{}")
    (root / "protocol.json").write_text(json.dumps(protocol))
    events = worker_events()
    events[-1][field] = value
    root.with_name("run.worker.jsonl").write_text("\n".join(json.dumps(row) for row in events))
    with pytest.raises(ValueError, match="within deadline"):
        gate.load_verified(root)


def test_worker_receipt_is_required_complete_and_matches_frozen_wall_limit(tmp_path):
    root = tmp_path / "run"
    protocol = {"worker_supervision": {"required": True, "wall_seconds": 1}}
    with pytest.raises(ValueError, match="unavailable"):
        gate.verify_worker_receipt(root, protocol)
    receipt = root.with_name("run.worker.jsonl")
    events = worker_events()
    receipt.write_text("\n".join(json.dumps(row) for row in events[:-1]))
    with pytest.raises(ValueError, match="incomplete"):
        gate.verify_worker_receipt(root, protocol)
    receipt.write_text("\n".join(json.dumps(row) for row in events))
    gate.verify_worker_receipt(root, protocol)
    protocol["worker_supervision"]["wall_seconds"] = 2
    with pytest.raises(ValueError, match="within deadline"):
        gate.verify_worker_receipt(root, protocol)
    with pytest.raises(ValueError, match="marker missing"):
        gate.verify_worker_receipt(root, {"source_files_sha256": {
            "integrations/software-repair/scripts/screen_deadline.py": "frozen"}})


def two_group_fixture(second_rewards):
    protocol, rows = fixture([1, .5, 1, .5], seed=1)
    other, tail = fixture(second_rewards, seed=2)
    protocol['groups'] += other['groups']
    protocol['required_productive_groups'] = 2
    return protocol, rows + tail


def test_declared_two_prompt_gate_cannot_pass_on_one_productive_group():
    protocol, rows = two_group_fixture([1, 1, 1, 1])
    result = gate.classify(protocol, rows)
    assert result['tasks']['task']['productive_groups'] == 1
    assert not result['genuine_signal_screened']
    protocol.pop('required_productive_groups')
    assert gate.classify(protocol, rows)['genuine_signal_screened']  # Legacy archives keep their original rule.


def test_both_productive_prompt_groups_meet_declared_requirement():
    protocol, rows = two_group_fixture([1, .5, 0, 1])
    result = gate.classify(protocol, rows)
    assert result['genuine_signal_screened'] and result['required_productive_groups'] == 2


@pytest.mark.parametrize('value', [0, True, 3, '2'])
def test_invalid_required_group_count_fails_closed(value):
    protocol, rows = two_group_fixture([1, .5, 0, 1])
    protocol['required_productive_groups'] = value
    with pytest.raises(ValueError, match='productive group requirement'):
        gate.classify(protocol, rows)


def test_confirmation_cannot_silently_lower_required_group_count():
    protocol, rows = two_group_fixture([1, .5, 0, 1])
    confirm_protocol, first = fixture([1, .5, 0, 1], seed=3, stage='confirm')
    other, second = fixture([1, .5, 0, 1], seed=4, stage='confirm')
    confirm_protocol['groups'] += other['groups']
    protocol['planned_confirmation_groups'] = confirm_protocol['groups']
    confirm_protocol['required_productive_groups'] = 1
    with pytest.raises(ValueError, match='unmatched confirmation settings'):
        gate.confirmation(protocol, gate.classify(protocol, rows), confirm_protocol,
                          gate.classify(confirm_protocol, first + second))
