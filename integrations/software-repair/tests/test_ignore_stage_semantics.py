"""Controlled wrong answers must stay semantic and confined to the missing function."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("stage_semantics", ROOT / "scripts/audit-ignore-stage-semantics.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize("level", [3, 4])
@pytest.mark.parametrize("seed", [1870000, 1870001])
def test_semantic_defects_offer_partial_credit_without_execution_failures(level, seed):
    row = MODULE.audit(level, seed)
    assert any(0 < variant["reward"] < 1 for variant in row["variants"])
    for variant in row["variants"]:
        assert not variant["public"]["errors"]
        assert not variant["hidden"]["errors"]
        assert 0 <= variant["reward"] <= 1


@pytest.mark.parametrize("level,defect", [(3, "parent_pruning"), (4, "negation")])
@pytest.mark.parametrize("seed", [1110000, 1110100, 1110200, 1110300])
def test_anonymous_replay_semantic_control_is_strictly_partial(level, defect, seed):
    row = MODULE.audit(level, seed)
    variant = next(v for v in row["variants"] if v["defect"] == defect)
    assert 0 < variant["reward"] < 1
    assert not variant["hidden"]["errors"]
