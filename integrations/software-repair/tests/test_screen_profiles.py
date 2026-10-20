import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("profile_fixture", Path(__file__).parents[1] / "scripts/screen_profiles.py")
profiles = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profiles)


def test_replay_profile_requires_new_arm_and_disjoint_confirmation():
    screen = profiles.get_profile("replay_compare", "screen")
    confirm = profiles.get_profile("replay_compare", "confirm")
    assert screen["signal_task_ids"] == confirm["signal_task_ids"] == ["software_repair-replay-d3"]
    assert screen["planned_confirmation_groups"] == confirm["groups"]
    assert {tuple(g) for g in screen["groups"]}.isdisjoint(tuple(g) for g in confirm["groups"])
    assert set(g[0] for g in screen["groups"]) == set(profiles.REPLAY_TASKS)
    for profile in (screen, confirm):
        assert len(profile["groups"]) == 4 and profile["max_calls"] == 192
        assert profile["samples_per_group"] == 4 and not profile["execution_enabled"]


def test_merge_comparison_is_locked_candidate_specific_and_disjoint_from_other_seeds():
    screen = profiles.get_profile("merge_compare", "screen")
    confirm = profiles.get_profile("merge_compare", "confirm")
    assert screen["signal_task_ids"] == confirm["signal_task_ids"] == ["software_repair-merge-d3"]
    assert screen["planned_confirmation_groups"] == confirm["groups"]
    seeds = [seed for stage in (screen, confirm) for _, seed in stage["groups"]]
    assert len(set(seeds)) == 4
    reserved = {seed for values in profiles.REPLAY_SEEDS.values() for seed in values}
    for start in (900000, 910000, 920000, 1076000, 1078000, 1080000, 1081000):
        reserved.update(range(start, start + 128))
    assert set(seeds).isdisjoint(reserved)
    for stage in (screen, confirm):
        assert len(stage["groups"]) == 4 and stage["max_calls"] == 192
        assert not stage["execution_enabled"] and stage["samples_per_group"] == 4
        assert stage["sampling_settings"] == profiles.sampling_settings()


def test_legacy_release_groups_stay_frozen_and_profiles_cannot_mutate_each_other():
    release = profiles.get_profile("release", "screen")
    assert release["groups"] == [["software_repair-release-d1", 1030000],
                                 ["software_repair-release-d1", 1030100]]
    assert release["max_calls"] == 96
    replay = profiles.get_profile("replay_compare", "screen")
    assert replay["sampling_settings"] == release["sampling_settings"]
    replay["groups"][0][0] = "changed"
    replay["sampling_settings"]["temperature"] = 0
    fresh = profiles.get_profile("replay_compare", "screen")
    assert fresh["groups"][0][0] == "software_repair-replay-d2"
    assert fresh["sampling_settings"]["temperature"] == .7


def test_small_probe_preserves_sampling_and_does_not_unlock_comparisons():
    screen = profiles.get_profile("merge_probe", "screen")
    confirm = profiles.get_profile("merge_probe", "confirm")
    assert screen["groups"] == [["software_repair-merge-d3", 1082000]]
    assert confirm["groups"] == [["software_repair-merge-d3", 1083000]]
    assert screen["planned_confirmation_groups"] == confirm["groups"]
    for value in (screen, confirm):
        assert value["max_calls"] == 48 and value["samples_per_group"] == 4
        assert value["signal_task_ids"] == ["software_repair-merge-d3"]
        assert value["sampling_settings"] == profiles.sampling_settings()
        assert value["execution_enabled"]
    for name in ("merge_compare", "replay_compare"):
        assert not profiles.get_profile(name, "screen")["execution_enabled"]


def test_reliability_probe_is_small_fresh_and_separate_from_signal_confirmation():
    value = profiles.get_profile("repair_reliability", "screen")
    assert value["groups"] == [["software_repair-merge-d3", 1086000]]
    assert value["planned_confirmation_groups"] == [["software_repair-merge-d3", 1087000]]
    assert value["samples_per_group"] == 2 and value["max_calls"] == 24
    assert value["purpose"] == "reliability_only"
    assert value["sampling_settings"]["stage_wall_seconds"] == 600
    assert value["sampling_settings"]["request_timeout_seconds"] == 180
    assert value["execution_enabled"]


def test_authorized_release_witness_preserves_frozen_prompts_and_sampling():
    screen = profiles.get_profile("release_witness", "screen")
    confirm = profiles.get_profile("release_witness", "confirm")
    assert screen["groups"] == [["software_repair-release-d2", 1091000],
                                 ["software_repair-release-d2", 1091100]]
    assert confirm["groups"] == [["software_repair-release-d2", 1092000],
                                  ["software_repair-release-d2", 1092100]]
    assert screen["planned_confirmation_groups"] == confirm["groups"]
    for value in (screen, confirm):
        assert value["samples_per_group"] == 4 and value["max_calls"] == 96
        assert value["signal_task_ids"] == ["software_repair-release-d2"]
        assert value["execution_enabled"]
        assert value["sampling_settings"] == profiles.sampling_settings()
    for name in ("replay_compare", "merge_compare"):
        assert not profiles.get_profile(name, "screen")["execution_enabled"]


@pytest.mark.parametrize("name,stage", [("unknown", "screen"), ("replay_compare", "unknown"), ("", "")])
def test_unknown_profile_or_stage_never_falls_back(name, stage):
    with pytest.raises(ValueError):
        profiles.get_profile(name, stage)
