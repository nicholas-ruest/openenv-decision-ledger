"""Frozen review profiles; the replay comparison has no paid execution path."""

MODEL = "Qwen/Qwen3.8-27B"
TOKENIZER_SHA = "0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3"
SAMPLES = 4
MAX_TURNS = 12
REQUEST_TIMEOUT_S = 180
REPLAY_TASKS = ("software_repair-replay-d2", "software_repair-replay-d3")
REPLAY_SEEDS = {"screen": (1060000, 1060100), "confirm": (1061000, 1061100)}
MERGE_TASKS = ("software_repair-merge-d2", "software_repair-merge-d3")
MERGE_SEEDS = {"screen": (1082000, 1082100), "confirm": (1083000, 1083100)}


def sampling_settings():
    return {"model": MODEL, "provider": "deepinfra", "tokenizer_sha256": TOKENIZER_SHA,
            "temperature": 0.7, "thinking_requested": True, "response_format": "json_object",
            "max_actions": MAX_TURNS, "episode_generation_observation_units": 8192,
            "context_units": 16384, "stage_wall_seconds": 1200,
            "request_timeout_seconds": REQUEST_TIMEOUT_S, "retries": 0}


def get_profile(name, stage):
    if stage not in ("screen", "confirm"):
        raise ValueError("unknown calibration stage")
    if name == "release":
        def groups(part):
            seeds = (1030000, 1030100) if part == "screen" else (1031000, 1031100)
            return [["software_repair-release-d1", seed] for seed in seeds]
        targets = ["software_repair-release-d1"]
    elif name == "replay_compare":
        def groups(part):
            return [[task, seed] for task in REPLAY_TASKS for seed in REPLAY_SEEDS[part]]
        targets = ["software_repair-replay-d3"]
    elif name == "merge_compare":
        def groups(part):
            return [[task, seed] for task in MERGE_TASKS for seed in MERGE_SEEDS[part]]
        targets = ["software_repair-merge-d3"]
    elif name == "merge_probe":
        # A single candidate prompt, not the larger locked comparison. Each
        # admission still requires the existing fresh, shared dollar receipt.
        def groups(part):
            seed = 1082000 if part == "screen" else 1083000
            return [["software_repair-merge-d3", seed]]
        targets = ["software_repair-merge-d3"]
    elif name == "repair_reliability":
        def groups(part):
            seed = 1086000 if part == "screen" else 1087000
            return [["software_repair-merge-d3", seed]]
        targets = ["software_repair-merge-d3"]
    elif name in ("release_witness", "release_witness_capacity"):
        def groups(part):
            if name == "release_witness_capacity":
                seeds = (1093000, 1093100) if part == "screen" else (1094000, 1094100)
            else:
                seeds = (1091000, 1091100) if part == "screen" else (1092000, 1092100)
            return [["software_repair-release-d2", seed] for seed in seeds]
        targets = ["software_repair-release-d2"]
    else:
        raise ValueError("unknown calibration profile")
    selected = groups(stage)
    samples = 2 if name == "repair_reliability" else SAMPLES
    settings = sampling_settings()
    if name == "release_witness_capacity":
        settings["episode_generation_observation_units"] = 12288
        settings["context_units"] = 24576
    if name == "repair_reliability":
        settings["stage_wall_seconds"] = 600
    return {"profile": name, "stage": stage, "groups": selected,
            "planned_confirmation_groups": groups("confirm"), "signal_task_ids": targets,
            "samples_per_group": samples, "max_calls": len(selected) * samples * MAX_TURNS,
            "sampling_settings": settings,
            "purpose": "reliability_only" if name == "repair_reliability" else "signal_screen",
            "execution_enabled": name in ("release", "merge_probe", "repair_reliability", "release_witness", "release_witness_capacity")}
