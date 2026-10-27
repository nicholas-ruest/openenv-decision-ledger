"""Packet generation must preserve exact native tasks and avoid accidental publishing."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("staged_packet", ROOT / "scripts/prepare-software-staged-review.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_request_pins_tested_image_and_one_category():
    value = MODULE.request()
    assert value["image"] == MODULE.IMAGE
    assert value["source"].endswith(MODULE.SOURCE)
    assert [t["task_id"] for t in value["tasks"]] == [t for t, _ in MODULE.PROFILES]
    assert all(t["tool_calls_total"] == 1 and t["completion_tokens"] == 8192 for t in value["tasks"])
    assert value["example_actions"] == [{"content": ""}]


@pytest.mark.parametrize("task_id,start", MODULE.PROFILES)
def test_fixture_has_native_reference_and_explicit_procedural_identity(task_id, start):
    row, passed = MODULE.fixture(task_id, start, "train")
    assert passed == 36
    assert row["kind"] == "procedural_fixture_not_captured_reset_observation"
    assert row["task_id"] == task_id and row["seed"] == start
    assert MODULE.digest(row["initial_source"].encode()) == row["initial_source_sha256"]


def test_existing_root_is_never_reused(tmp_path):
    with pytest.raises(FileExistsError):
        MODULE.build(tmp_path)
