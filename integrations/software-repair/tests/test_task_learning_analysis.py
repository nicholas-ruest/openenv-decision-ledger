"""Protect exact-step joins and unknown task identity in training diagnostics."""
import importlib.util
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[3] / "scripts/analyze-task-learning.py"
SPEC = importlib.util.spec_from_file_location("task_learning", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def rows(pairs):
    return [{"step": step, "value": value} for step, value in pairs]


def test_join_uses_recorded_identity_and_excludes_retries():
    data = {
        "step/task": rows([(9, 2), (1, 2), (4, 1)]),
        "reward": rows([(4, 1), (1, .5), (9, 0)]),
        "reward_std": rows([(1, .2), (4, 0), (9, 0)]),
        "grad_norm": rows([(9, 0), (4, 0), (1, .1)]),
        "step/retries": rows([(1, 0), (4, 0), (9, 1)]),
    }
    result = MODULE.analyze(data)
    assert result["groups"]["2"]["productive_clean_steps"] == 1
    assert result["groups"]["2"]["retried_steps"] == 1
    assert result["groups"]["2"]["mean_clean_reward"] == .5
    assert result["groups"]["1"]["saturated_clean_steps"] == 1
    assert result["groups"]["1"]["task_name"] is None


def test_missing_is_not_zero_and_unassigned_is_reported():
    result = MODULE.analyze({"step/task": rows([(1, 1)]),
                             "reward": rows([(1, 1), (2, .5)])})
    assert result["groups"]["1"]["clean_steps"] == 0
    assert result["groups"]["1"]["incomplete_steps"] == 1
    assert result["groups"]["1"]["mean_clean_reward"] is None
    assert result["unassigned_metric_steps"]["reward"] == [2]


@pytest.mark.parametrize("pairs", [[(1, 0), (1, 1)], [(True, 1)],
                                  [(1, float("nan"))], [(1, "x")]])
def test_ambiguous_or_invalid_metrics_rejected(pairs):
    with pytest.raises(ValueError):
        MODULE.index_rows(rows(pairs))


def test_noninteger_task_rejected():
    with pytest.raises(ValueError):
        MODULE.analyze({"step/task": rows([(1, 1.5)])})
