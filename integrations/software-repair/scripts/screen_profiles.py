"""Frozen review profiles; the replay comparison has no paid execution path."""

MODEL = "Qwen/Qwen3.8-27B"
TOKENIZER_SHA = "0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3"
SAMPLES = 4
MAX_TURNS = 12
REPLAY_TASKS = ("software_repair-replay-d2", "software_repair-replay-d3")
REPLAY_SEEDS = {"screen": (1060000, 1060100), "confirm": (1061000, 1061100)}


def sampling_settings():
    return {"model": MODEL, "provider": "deepinfra", "tokenizer_sha256": TOKENIZER_SHA,
            "temperature": 0.7, "thinking_requested": True, "response_format": "json_object",
            "max_actions": MAX_TURNS, "episode_generation_observation_units": 8192,
            "context_units": 16384, "stage_wall_seconds": 1200, "retries": 0}


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
    else:
        raise ValueError("unknown calibration profile")
    selected = groups(stage)
    return {"profile": name, "stage": stage, "groups": selected,
            "planned_confirmation_groups": groups("confirm"), "signal_task_ids": targets,
            "samples_per_group": SAMPLES, "max_calls": len(selected) * SAMPLES * MAX_TURNS,
            "sampling_settings": sampling_settings(), "execution_enabled": name == "release"}
