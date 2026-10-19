import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("signal_gate", Path(__file__).parents[1] / "scripts/analyze_screen.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def fixture(rewards, failures=None, seed=1, stage="screen"):
    failures = failures or [None] * len(rewards)
    protocol = {"groups": [["task", seed]], "samples_per_group": 4, "stage": stage,
                "provider": {"id": "fixed"}, "source_files_sha256": {"file": "fixed"}, "tokenizer_sha256": "fixed",
                "planned_confirmation_groups": [["task", seed+1]]}
    rows = [{"task_id": "task", "seed": seed, "sample": i, "reward": reward,
             "solved": reward == 1, "failure": failure, "prompt_sha256": "a" * 64,
             "hidden_execution_rejections": 0, "hidden_wrong_answers": int(reward != 1)}
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


def test_confirmation_needs_fresh_matched_productive_prompts_and_never_authorizes_submission():
    p, rows = fixture([1, .8, 0, 1])
    q, fresh = fixture([1, 1, .9, 1], seed=2, stage="confirm")
    result = gate.confirmation(p, gate.classify(p, rows), q, gate.classify(q, fresh))
    assert result["provisional_single_family_signal_confirmed"]
    assert not result["is_model_improvement"] and not result["arena_submission_authorized"]
    q["provider"] = {"id": "changed"}
    with pytest.raises(ValueError):
        gate.confirmation(p, gate.classify(p, rows), q, gate.classify(q, fresh))
