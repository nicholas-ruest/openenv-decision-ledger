import copy
import json
from pathlib import Path

import pytest

from arena_env.environment import ArenaAction, ArenaEnvironment
from arena_env.tasks import make_task, oracle_answer
from training.adapter import encode
from training.config import TrainingConfig, SeedRange
from training.cpu_smoke import tiny_components
from training.session import dataset_for, main, run_session


def test_focused_session_real_optimizer_reload_and_export(tmp_path):
    import torch
    torch.set_num_threads(2)
    config = TrainingConfig.model_validate_json(Path("config/private-training-preparation.json").read_text())
    config = config.model_copy(update={"train_seeds": SeedRange(start=950000, count=1),
        "max_steps": 2, "max_completion_tokens": 512, "max_context_tokens": 4096,
        "max_optimizer_steps": 1, "learning_rate": 0.001, "thinking": False})
    expected = oracle_answer(make_task("software_change", 950000, 2))
    partial = copy.deepcopy(expected)
    partial.pop("build_order")
    actions = [json.dumps({"op": "submit", "answer": x}) for x in [expected, partial, {}, expected]]
    env = ArenaEnvironment()
    reset = env.reset(task_id="software_change-d2", seed=950000).model_dump_json()
    read = env.step(ArenaAction(op="read", path="*")).model_dump_json()
    bundle = tiny_components([reset, read, *actions], "qwen3_5")
    tokenizer = bundle[1]
    def sample(ids, occurrence, turn, allowance):
        action = '{"op":"read","path":"*"}' if turn == 0 else actions[occurrence % 4]
        return encode(tokenizer, action + "<|im_end|>")
    report = run_session(config, Path("integrations/openenv-arena"), tmp_path / "session",
                         bundle=bundle, sampler=sample, diagnostic=True)
    assert report["status"] == "completed" and report["optimizer_steps"] == 1
    assert report["adapter_changed"] and report["reload_equal"]
    assert len(report["audit"]) == 4
    assert (tmp_path / "session/checkpoint.tar.gz").is_file()
    assert report["target_model_training"] is False


def test_paid_cli_is_locked_before_model_load(monkeypatch):
    monkeypatch.setattr("sys.argv", ["session", "--execute"])
    with pytest.raises(SystemExit, match="locked"):
        main()
