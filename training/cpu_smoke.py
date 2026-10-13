"""Offline diagnostic fixture: real TRL backward/save/reload, tiny random model.

Scripted actions exercise the native verifier and loss masks. They are explicitly
off-policy fixtures, never evidence of policy learning or Arena performance.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path


def tiny_components(corpus: list[str]):
    import torch
    from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers
    from transformers import GPT2Config, GPT2LMHeadModel, PreTrainedTokenizerFast

    torch.manual_seed(123)
    backend = Tokenizer(models.BPE(unk_token="<unk>"))
    backend.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    backend.decoder = decoders.ByteLevel()
    backend.train_from_iterator(corpus, trainers.BpeTrainer(
        vocab_size=1000,
        initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
        special_tokens=["<pad>", "<unk>", "<|im_start|>", "<|im_end|>"],
    ))
    tokenizer = PreTrainedTokenizerFast(
        tokenizer_object=backend, pad_token="<pad>", unk_token="<unk>",
        eos_token="<|im_end|>", padding_side="left",
    )
    tokenizer.chat_template = (
        "{% for m in messages %}{{ '<|im_start|>' + m['role'] + '\\n' "
        "+ m['content'] + '<|im_end|>\\n' }}{% endfor %}"
        "{% if add_generation_prompt %}{{ '<|im_start|>assistant\\n' }}{% endif %}"
    )
    model = GPT2LMHeadModel(GPT2Config(
        vocab_size=len(tokenizer), n_positions=4096, n_ctx=4096,
        n_embd=16, n_layer=1, n_head=2, resid_pdrop=0,
        embd_pdrop=0, attn_pdrop=0, eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.pad_token_id, bos_token_id=None,
    ))
    return model, tokenizer


def run_cpu_smoke(output: Path) -> dict:
    import torch
    from datasets import Dataset
    from transformers import GPT2LMHeadModel
    from trl import GRPOConfig, GRPOTrainer

    from arena_env.environment import ArenaAction, ArenaEnvironment
    from arena_env.tasks import make_task, oracle_answer
    from training.adapter import JsonArenaRollout, RolloutLimits, encode, native_reward

    torch.set_num_threads(2)
    output.mkdir(parents=True, exist_ok=False)
    task_id, seed = "software_change-d2", 930000
    task = make_task("software_change", seed, 2)
    expected = oracle_answer(task)
    partial = copy.deepcopy(expected)
    partial.pop("build_order")
    answers = [expected, partial, {}, expected]
    actions = [json.dumps({"op": "submit", "answer": answer}) for answer in answers]
    env = ArenaEnvironment()
    reset = env.reset(task_id=task_id, seed=seed).model_dump_json()
    read = env.step(ArenaAction(op="read", path="*")).model_dump_json()
    model, tokenizer = tiny_components([reset, read, *actions])
    before = {name: value.detach().clone() for name, value in model.named_parameters()}

    def scripted(input_ids, occurrence, turn, allowance):
        action = '{"op":"read","path":"*"}' if turn == 0 else actions[occurrence % 4]
        return encode(tokenizer, action + "<|im_end|>")

    adapter = JsonArenaRollout(tokenizer, RolloutLimits(
        max_steps=2, completion_tokens=512, context_tokens=4096,
        thinking=False,
    ), sampler=scripted)
    descriptor = [{"role": "user", "content": json.dumps({"task_id": task_id, "seed": seed})}]
    dataset = Dataset.from_dict({"prompt": [descriptor] * 2})
    trainer = GRPOTrainer(
        model=model, processing_class=tokenizer, reward_funcs=native_reward,
        rollout_func=adapter, train_dataset=dataset,
        args=GRPOConfig(
            output_dir=str(output / "trainer"), use_cpu=True, bf16=False,
            fp16=False, max_steps=1, num_generations=4,
            per_device_train_batch_size=4, gradient_accumulation_steps=1,
            max_completion_length=512, learning_rate=0.001,
            gradient_checkpointing=False, optim="adamw_torch",
            beta=0, loss_type="dapo", report_to="none",
            save_strategy="no", logging_steps=1, disable_tqdm=True,
            remove_unused_columns=False, use_vllm=False,
        ),
    )
    train_output = trainer.train()
    changed = sum(not torch.equal(before[name], value.detach())
                  for name, value in model.named_parameters())
    if not changed:
        raise RuntimeError("Diagnostic backward/optimizer step did not change parameters")
    if len(adapter.audit) != 4:
        raise RuntimeError("TRL prompt duplication contract mismatch")
    rewards = [x["reward"] for x in adapter.audit]
    if rewards != [1.0, 0.75, 0.0, 1.0]:
        raise RuntimeError(f"Native diagnostic rewards changed: {rewards}")
    checkpoint = output / "checkpoint"
    trainer.save_model(str(checkpoint))
    loaded = GPT2LMHeadModel.from_pretrained(checkpoint, local_files_only=True)
    for key, value in model.state_dict().items():
        if not torch.equal(value.cpu(), loaded.state_dict()[key]):
            raise RuntimeError("Checkpoint reload differs")
    # Independently exercise the real policy generation path with a tiny budget.
    generated = JsonArenaRollout(tokenizer, RolloutLimits(
        max_steps=2, completion_tokens=8, context_tokens=4096, thinking=False,
    ))([descriptor], trainer)
    if sum(generated["env_mask"][0]) > 8:
        raise RuntimeError("Generation exceeded its token budget")
    report = {
        "status": "passed", "device": "cpu", "downloaded_model": False,
        "diagnostic_fixture": True, "on_policy_learning_claim": False,
        "target_model_training": False, "target_gpu_memory_verified": False,
        "trl_optimizer_steps": train_output.global_step,
        "changed_parameter_tensors": changed, "native_rewards": rewards,
        "rollout_instances": len(adapter.audit),
        "observation_tokens_masked": [x["observation_tokens"] for x in adapter.audit],
        "checkpoint_save_reload_equal": True,
        "real_generation_path_status": generated["rollout_status"],
        "limitations": [
            "Scripted off-policy actions are fixtures, not evidence of model improvement.",
            "Tiny CPU model success does not establish 27B GPU memory compatibility.",
            "ChatML wrapper is an explicit private proxy, not verified Arena equivalence.",
        ],
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
