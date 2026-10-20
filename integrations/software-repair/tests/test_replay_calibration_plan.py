"""Ensure a future review packet cannot imply calls or reuse prompt identities."""
import importlib.util
import json
from pathlib import Path

import pytest

from repair_env.tasks import make_task, visible_files

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("replay_plan", ROOT / "scripts/plan-replay-calibration.py")
plan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plan)


def test_review_packet_freezes_disjoint_reproducible_groups_without_execution():
    result = plan.build()
    assert result["plan_version"] == 2 and result["profile"] == "replay_compare"
    assert result["signal_task_ids"] == ["software_repair-replay-d3"]
    assert result["executed"] is False and result["paid_execution_allowed"] is False
    assert result["new_model_calls"] == 0 and not result["arena_submission_authorized"]
    assert result["is_training"] is False and result["mix_adoption"] is False
    groups = [g for stage in result["stages"].values() for g in stage["groups"]]
    assert len(groups) == len({g["workspace_sha256"] for g in groups}) == 8
    assert len({g["task_fingerprint"] for g in groups}) == 8
    for group in groups:
        assert plan.digest(visible_files(make_task(group["task_id"], group["seed"]))) == group["workspace_sha256"]
    for stage in result["stages"].values():
        assert stage["samples_per_prompt"] == 4 and stage["planned_rollouts"] == 16
        assert stage["max_calls"] == 192
    assert set(plan.SEEDS["screen"]).isdisjoint(plan.SEEDS["confirm"])
    reserved = set(range(900000, 900128)) | set(range(910000, 910032)) | set(range(920000, 920064))
    for start in (1050000, 1051000, 1052000, 1055000):
        reserved.update(range(start, start + 8))
    assert not reserved.intersection(seed for seeds in plan.SEEDS.values() for seed in seeds)


def test_packet_cli_refuses_overwrite_and_has_no_execute_mode(tmp_path):
    output = tmp_path / "packet.json"
    assert plan.main(["--output", str(output)]) == 0
    saved = output.read_bytes()
    assert not json.loads(saved)["executed"]
    with pytest.raises(FileExistsError):
        plan.main(["--output", str(output)])
    assert output.read_bytes() == saved
    with pytest.raises(SystemExit) as error:
        plan.main(["--execute"])
    assert error.value.code == 2


def test_merge_packet_freezes_both_arms_but_only_new_candidate_may_qualify(tmp_path):
    result = plan.build("merge_compare")
    assert result["profile"] == "merge_compare" and result["signal_task_ids"] == ["software_repair-merge-d3"]
    assert result["confirmation_conditional_on_candidate_signal"]
    assert not result["executed"] and not result["paid_execution_allowed"]
    groups = [group for stage in result["stages"].values() for group in stage["groups"]]
    assert len(groups) == len({g["workspace_sha256"] for g in groups}) == 8
    assert {g["task_id"] for g in groups} == {"software_repair-merge-d2", "software_repair-merge-d3"}
    assert all(stage["planned_rollouts"] == 16 and stage["max_calls"] == 192 for stage in result["stages"].values())
    assert "integrations/software-repair/repair_env/merge_curriculum.py" in result["source_files_sha256"]
    assert plan.main(["--profile", "merge_compare", "--output", str(tmp_path / "merge.json")]) == 0
    with pytest.raises(ValueError, match="offline comparison"):
        plan.build("release")
