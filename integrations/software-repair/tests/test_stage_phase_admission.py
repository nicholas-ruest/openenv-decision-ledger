"""Admission never silently shrinks a phase or borrows another allocation."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("admission", ROOT / "scripts/stage-phase-admission.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_complete_phase_exact_cost_and_boundary():
    value = MODULE.admit(2, [1000, 1000], 1000, {"input": 1, "output": 1}, ".0044")
    assert value["admitted"] and value["quoted_usd"] == "0.0044"
    assert not value["reservation_performed"]
    assert not MODULE.admit(2, [1000, 1000], 1000, {"input": 1, "output": 1}, ".004399")["admitted"]


@pytest.mark.parametrize("remaining", ["NaN", "Infinity", "-1"])
def test_invalid_ledger_amount_is_not_unlimited(remaining):
    with pytest.raises(ValueError):
        MODULE.admit(1, [1000], 1000, {"input": 1, "output": 1}, remaining)


def test_incomplete_quotes_cannot_admit_partial_experiment():
    with pytest.raises(ValueError):
        MODULE.admit(24, [1000] * 16, 8192, {"input": .2, "output": 2.5}, "1")
