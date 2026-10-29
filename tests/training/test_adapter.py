"""Native rollout isolation, masking, budget and split checks."""
import json
from pathlib import Path

import pytest

from arena_env.environment import ArenaEnvironment
from arena_env.tasks import make_task, oracle_answer
from training.adapter import JsonArenaRollout, RolloutLimits, encode, native_reward, parse_action
from training.config import TrainingConfig, verify_runtime
from training.cpu_smoke import tiny_components


@pytest.fixture
def tokenizer():
    _, tokenizer = tiny_components([
        '{"op":"read","path":"*"}', '{"op":"submit","answer":{}}'
    ])
    return tokenizer


def prompt(seed=940000):
    return [{"role": "user", "content": json.dumps({
        "task_id": "software_change-d2", "seed": seed
    })}]


def test_rollouts_own_independent_native_environments_and_mask_feedback(tokenizer):
    envs = []

    def factory():
        env = ArenaEnvironment()
        envs.append(env)
        return env

    def sampler(ids, occurrence, turn, allowance):
        if turn == 0:
            action = '{"op":"read","path":"*"}'
        else:
            answer = oracle_answer(make_task("software_change", 940000, 2))
            action = json.dumps({"op": "submit", "answer": answer if occurrence == 0 else {}})
        return encode(tokenizer, action + "<|im_end|>")

    adapter = JsonArenaRollout(tokenizer, RolloutLimits(
        thinking=False, context_tokens=12000, completion_tokens=4096,
    ), sampler=sampler, env_factory=factory)
    result = adapter([prompt(), prompt()], None)
    assert len(envs) == 2 and envs[0] is not envs[1]
    assert result["prompt_ids"][0] == result["prompt_ids"][1]
    assert result["native_rewards"] == [1.0, 0.0]
    for ids, mask in zip(result["completion_ids"], result["env_mask"]):
        assert len(ids) == len(mask)
        assert 0 in mask and 1 in mask
        assert sum(mask) <= 4096
    assert all(x["observation_tokens"] > 0 for x in adapter.audit)


def test_sampler_cannot_exceed_budget(tokenizer):
    adapter = JsonArenaRollout(tokenizer, RolloutLimits(
        thinking=False, context_tokens=12000, completion_tokens=4,
    ), sampler=lambda ids, occurrence, turn, allowance: [1] * 5)
    with pytest.raises(ValueError, match="budget"):
        adapter([prompt()], None)


def test_truncation_is_not_counted_as_wrong_answer(tokenizer):
    adapter = JsonArenaRollout(tokenizer, RolloutLimits(
        thinking=False, context_tokens=12000, completion_tokens=4,
    ), sampler=lambda ids, occurrence, turn, allowance: [1] * 4)
    result = adapter([prompt()], None)
    assert result["rollout_status"] == ["truncated"]
    assert native_reward([], result["native_rewards"], result["rollout_status"]) == [None]


@pytest.mark.parametrize("text", [
    '{"op":"read","path":"*","surprise":1}',
    '{"op":"submit","answer":{"x":NaN}}',
    '```json\n{"op":"submit","answer":{}}\n```',
])
def test_invalid_actions_fail_closed(text):
    with pytest.raises(ValueError):
        parse_action(text, False)


def test_complete_thinking_prefix_and_strict_json():
    assert parse_action('some reasoning\n</think>\n{"op":"read","path":"*"}', True).op == "read"
    with pytest.raises(ValueError, match="Incomplete"):
        parse_action('{"op":"read","path":"*"}', True)


def test_disjoint_seed_ranges_and_unconfirmed_readiness():
    path = Path("config/private-training-preparation.json")
    config = TrainingConfig.model_validate_json(path.read_text())
    assert "task_mix_unconfirmed" in config.blockers()
    data = config.model_dump()
    data["validation_seeds"]["start"] = data["train_seeds"]["start"]
    with pytest.raises(ValueError, match="overlap"):
        TrainingConfig.model_validate(data)


def test_runtime_drift_is_rejected(tmp_path):
    config = TrainingConfig.model_validate_json(
        Path("config/private-training-preparation.json").read_text()
    )
    (tmp_path / "arena_env").mkdir()
    (tmp_path / "arena_env/environment.py").write_text("changed")
    with pytest.raises(ValueError, match="changed"):
        verify_runtime(config, tmp_path)
