"""Offline mocked lifecycle tests. No credential or actual model call is used."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import time

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("probe_runner", ROOT / "scripts/run-software-scaffold-probe.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def expected():
    return {"task_id": MODULE.TASKS[0], "seed": MODULE.SEEDS[0],
            "base_prompt_sha256": "a" * 64, "messages": [{"role": "user", "content": "fixture"}],
            **{k: "b" * 64 for k in ("case_sha256", "reset_sha256", "workspace_sha256", "prompt_sha256")}}


def row(sample):
    e = expected()
    return {"task_id": e["task_id"], "seed": e["seed"], "sample": sample,
            "prompt_sha256": e["base_prompt_sha256"], "messages": e["messages"],
            "calls": [{"client_call_label": str(sample), "provider_response_id_sha256": str(sample) * 64}],
            "failure": None, "reward": .75}


def test_collect_samples_exactly_once_and_saves_raw_before_assessment():
    seen, saved = [], []
    def episode(task, seed, sample, *args):
        seen.append(sample)
        return row(sample)
    result = MODULE.collect(SimpleNamespace(episode=episode), [expected()], None, None, None,
                            {}, {}, time.monotonic() + 5, "test", saved.append)
    assert sorted(seen) == [0, 1, 2, 3] and len(saved) == len(result) == 4


def test_deadline_prevents_admission():
    def episode(*args):
        raise AssertionError("expired call must not launch")
    assert MODULE.collect(SimpleNamespace(episode=episode), [expected()], None, None, None,
                          {}, {}, time.monotonic() - 1, "test", lambda _: None) == []


def test_actual_reset_mismatch_preserves_raw_and_fails():
    saved = []
    def episode(task, seed, sample, *args):
        value = row(sample)
        value["prompt_sha256"] = "c" * 64
        return value
    with pytest.raises(ValueError):
        MODULE.collect(SimpleNamespace(episode=episode), [expected()], None, None, None,
                       {}, {}, time.monotonic() + 5, "test", saved.append)
    assert len(saved) == 4


@pytest.mark.parametrize("failure,category", [("invalid_json_action", "format"),
    ("completion_truncated", "truncation"), ("candidate_execution_failure", "execution"),
    ("screen_reservation_cap_exhausted", "budget"), ("unrecognized_internal_error", "provider")])
def test_failure_never_becomes_wrong_answer(failure, category):
    assert MODULE.classify({"failure": failure}) == category
