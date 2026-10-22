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
    elif name == "release_stream_probe":
        def groups(part):
            return [["software_repair-release-d3", 1102000]] if part == "screen" else []
        targets = ["software_repair-release-d3"]
    elif name in ("direct_release", "direct_release_control"):
        def groups(part):
            seeds = (1111000, 1111100) if part == "screen" else (1112000, 1112100)
            return [["software_repair-release-d3", seed] for seed in seeds]
        targets = ["software_repair-release-d3"]
    elif name in ("release_generalization", "release_generalization_stream"):
        streamed = name == "release_generalization_stream"
        def groups(part):
            if streamed:
                seeds = (1104000, 1104100) if part == "screen" else (1105000, 1105100)
            else:
                seeds = (1100000, 1100100) if part == "screen" else (1101000, 1101100)
            return [["software_repair-release-d3", seed] for seed in seeds]
        targets = ["software_repair-release-d3"]
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
    samples = 2 if name in ("repair_reliability", "release_stream_probe") else SAMPLES
    settings = sampling_settings()
    if name in ("direct_release", "direct_release_control"):
        settings.update(interface="direct_code" if name == "direct_release" else "interactive",
            max_actions=1 if name == "direct_release" else MAX_TURNS,
            max_generation_per_call=8192, episode_generation_observation_units=12288,
            context_units=24576, provider_streaming=True)
    if name in ("release_witness_capacity", "release_generalization", "release_stream_probe", "release_generalization_stream"):
        settings["episode_generation_observation_units"] = 12288
        settings["context_units"] = 24576
    if name in ("release_stream_probe", "release_generalization_stream"):
        settings["provider_streaming"] = True
    if name in ("repair_reliability", "release_stream_probe"):
        settings["stage_wall_seconds"] = 600
    return {**({"required_productive_groups": 2} if name in ("release_generalization_stream", "direct_release", "direct_release_control") else {}),
            "profile": name, "stage": stage, "groups": selected,
            "planned_confirmation_groups": groups("confirm"), "signal_task_ids": targets,
            "samples_per_group": samples, "max_calls": len(selected) * samples * settings["max_actions"],
            "sampling_settings": settings,
            "purpose": "reliability_only" if name in ("repair_reliability", "release_stream_probe") else "signal_screen",
            "execution_enabled": name in ("release", "merge_probe", "repair_reliability", "release_witness", "release_witness_capacity", "release_generalization", "release_generalization_stream", "direct_release", "direct_release_control")
                or (name == "release_stream_probe" and stage == "screen")}
