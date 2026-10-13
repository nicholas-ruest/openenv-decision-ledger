"""Native JSON-action rollouts for TRL 1.6.0, with observation loss masking.

This uses an explicit ChatML wrapper and Transformers generation on the local
policy. It is a private proxy protocol; Arena's production chat wrapper is not
known. No hosted inference trajectories are replayed as on-policy training.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Callable

from arena_env.environment import ArenaAction, ArenaEnvironment
from arena_env.tasks import parse_task_id


SYSTEM = (
    "Operate the virtual file environment. Return one JSON ACTION INSTANCE. "
    'First read {"op":"read","path":"*"}. Then solve the task and return '
    '{"op":"submit","answer":{...}}. Do not return a JSON schema or markdown.'
)


@dataclass(frozen=True)
class RolloutLimits:
    max_steps: int = 4
    completion_tokens: int = 8192
    context_tokens: int = 16384
    temperature: float = 0.7
    thinking: bool = True


def encode(tokenizer, text: str) -> list[int]:
    return tokenizer.encode(text, add_special_tokens=False)


def assistant_header(thinking: bool) -> str:
    return "<|im_start|>assistant\n" + ("<think>\n" if thinking else "")


def initial_tokens(tokenizer, observation: str, thinking: bool) -> list[int]:
    return encode(
        tokenizer,
        "<|im_start|>system\n" + SYSTEM + "<|im_end|>\n"
        + "<|im_start|>user\n" + observation + "<|im_end|>\n"
        + assistant_header(thinking),
    )


def parse_action(text: str, thinking: bool) -> ArenaAction:
    """Accept strict native actions; remove only a complete reasoning prefix."""
    text = text.strip()
    if thinking:
        # The opening <think> is prefilled in the assistant header.
        if "</think>" not in text:
            raise ValueError("Incomplete reasoning block")
        text = text.split("</think>", 1)[1].strip()
    value = json.loads(text, parse_constant=lambda _: (_ for _ in ()).throw(
        ValueError("Nonfinite JSON")
    ))
    if type(value) is not dict or set(value) - {"op", "path", "answer", "metadata"}:
        raise ValueError("Unknown action fields")
    return ArenaAction.model_validate(value, strict=True)


class JsonArenaRollout:
    """Create a fresh native environment for every prompt occurrence."""

    def __init__(
        self, tokenizer, limits: RolloutLimits, *,
        deadline: float | None = None,
        sampler: Callable | None = None,
        env_factory: Callable = ArenaEnvironment,
    ):
        self.tokenizer = tokenizer
        self.limits = limits
        self.deadline = deadline
        self.sampler = sampler
        self.env_factory = env_factory
        self.audit: list[dict] = []
        for special in ("<|im_start|>", "<|im_end|>"):
            token = tokenizer.convert_tokens_to_ids(special)
            if token is None or token == tokenizer.unk_token_id:
                raise ValueError("Tokenizer must support explicit ChatML special tokens")

    def _sample(self, input_ids, trainer, allowance: int, occurrence: int, turn: int):
        if self.sampler is not None:
            return self.sampler(input_ids, occurrence, turn, allowance)
        import torch
        from transformers import StoppingCriteria, StoppingCriteriaList

        deadline = self.deadline

        class DeadlineStop(StoppingCriteria):
            def __call__(self, input_ids, scores, **kwargs):
                return deadline is not None and time.monotonic() >= deadline

        ids = torch.tensor([input_ids], device=trainer.accelerator.device)
        model = trainer.accelerator.unwrap_model(trainer.model)
        was_training = model.training
        try:
            model.eval()
            with torch.no_grad():
                output = model.generate(
                    ids,
                    attention_mask=torch.ones_like(ids),
                    do_sample=True,
                    temperature=self.limits.temperature,
                    max_new_tokens=allowance,
                    eos_token_id=self.tokenizer.convert_tokens_to_ids("<|im_end|>"),
                    pad_token_id=self.tokenizer.pad_token_id,
                    stopping_criteria=StoppingCriteriaList([DeadlineStop()]),
                    use_cache=True,
                )
            return output[0, len(input_ids):].tolist()
        finally:
            model.train(was_training)

    def __call__(self, prompts: list, trainer) -> dict:
        # TRL's sampler already repeats rows num_generations times. Do not
        # multiply this list again: every occurrence owns one environment.
        result = {key: [] for key in (
            "prompt_ids", "completion_ids", "env_mask", "native_rewards",
            "rollout_status", "task_ids", "prompt_seeds"
        )}
        result["logprobs"] = None  # Same local policy; TRL computes old logprobs.
        for occurrence, prompt in enumerate(prompts):
            descriptor = json.loads(prompt[-1]["content"])
            task, seed = descriptor["task_id"], descriptor["seed"]
            parse_task_id(task)
            if type(seed) is not int or seed < 0:
                raise ValueError("Seed must be a nonnegative integer")
            env = self.env_factory()
            obs = env.reset(task_id=task, seed=seed)
            prefix = initial_tokens(self.tokenizer, obs.model_dump_json(), self.limits.thinking)
            if len(prefix) >= self.limits.context_tokens:
                raise ValueError("Reset observation exceeds context budget")
            continuation, mask = [], []
            generated_count, reward, status = 0, 0.0, "step_limit"
            for turn in range(self.limits.max_steps):
                if self.deadline is not None and time.monotonic() >= self.deadline:
                    raise TimeoutError("Training wall-time limit reached")
                allowance = min(
                    self.limits.completion_tokens - generated_count,
                    self.limits.context_tokens - len(prefix) - len(continuation),
                )
                if allowance <= 0:
                    status = "token_limit"
                    break
                generated = list(self._sample(
                    prefix + continuation, trainer, allowance, occurrence, turn
                ))
                if not generated or len(generated) > allowance:
                    raise ValueError("Sampler exceeded generation budget or returned no tokens")
                continuation.extend(generated)
                mask.extend([1] * len(generated))
                generated_count += len(generated)
                stop_ids = {self.tokenizer.eos_token_id,
                            self.tokenizer.convert_tokens_to_ids("<|im_end|>")}
                stopped = generated[-1] in stop_ids
                if not stopped:
                    status = "truncated"
                    break
                text = self.tokenizer.decode(generated[:-1], skip_special_tokens=False)
                try:
                    action = parse_action(text, self.limits.thinking)
                except (ValueError, TypeError):
                    status = "invalid_action"
                    break
                obs = env.step(action)
                if obs.done:
                    reward, status = float(obs.reward), "terminal"
                    break
                feedback = encode(
                    self.tokenizer,
                    "\n<|im_start|>user\n" + obs.model_dump_json()
                    + "<|im_end|>\n" + assistant_header(self.limits.thinking),
                )
                if len(prefix) + len(continuation) + len(feedback) >= self.limits.context_tokens:
                    status = "context_limit"
                    break
                continuation.extend(feedback)
                mask.extend([0] * len(feedback))
            result["prompt_ids"].append(prefix)
            result["completion_ids"].append(continuation)
            result["env_mask"].append(mask)
            result["native_rewards"].append(reward)
            result["rollout_status"].append(status)
            result["task_ids"].append(task)
            result["prompt_seeds"].append(seed)
            self.audit.append({"task_id": task, "seed": seed, "reward": reward,
                               "full_solve": reward == 1.0, "status": status,
                               "generated_tokens": generated_count,
                               "observation_tokens": len(mask) - sum(mask)})
        return result


def native_reward(completions, native_rewards, rollout_status, **kwargs) -> list:
    """Exclude invalid/truncated episodes from learning-signal statistics."""
    return [reward if status == "terminal" else None
            for reward, status in zip(native_rewards, rollout_status, strict=True)]
