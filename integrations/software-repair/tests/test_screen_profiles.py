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


@pytest.mark.parametrize("name,stage", [("unknown", "screen"), ("replay_compare", "unknown"), ("", "")])
def test_unknown_profile_or_stage_never_falls_back(name, stage):
    with pytest.raises(ValueError):
        profiles.get_profile(name, stage)
