"""Focused local GRPO/LoRA session. CLI paid execution stays locked."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import time
from pathlib import Path

from training.config import TrainingConfig, checkpoint_tree_sha256, verify_runtime
from training.lifecycle import export_checkpoint


def dataset_for(config):
    from datasets import Dataset
    if config.task_ids != ["software_change-d2"]:
        raise ValueError("Focused session accepts one software task only")
    return Dataset.from_dict({"prompt": [[{"role": "user", "content": json.dumps({
        "task_id": config.task_ids[0], "seed": seed})}] for seed in config.train_seeds.seeds()]})


def load_target(config):
    """Local pinned weights only. Never resolves Hub credentials or downloads."""
    import torch
    from transformers import AutoModelForImageTextToText, AutoTokenizer
    path = Path(config.model_path or "")
    if not config.model_path or not path.is_dir():
        raise ValueError("Frozen local checkpoint required")
    from training.checkpoint_manifest import verify_checkpoint
    verify_checkpoint(config, path)
    if hashlib.sha256((path / "tokenizer.json").read_bytes()).hexdigest() != config.tokenizer_sha256:
        raise ValueError("Tokenizer changed")
    metadata = json.loads((path / "config.json").read_text())
    if metadata.get("model_type") != "qwen3_5":
        raise ValueError("Unexpected target architecture")
    model = AutoModelForImageTextToText.from_pretrained(
        path, local_files_only=True, trust_remote_code=False, dtype=torch.bfloat16,
        attn_implementation="eager")
    tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True,
                                              trust_remote_code=False, padding_side="left")
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    return model, tokenizer


def adapter_digest(model):
    from peft import get_peft_model_state_dict
    h = hashlib.sha256()
    for name, tensor in sorted(get_peft_model_state_dict(model).items()):
        h.update(name.encode())
        h.update(str(tensor.shape).encode())
        h.update(tensor.detach().cpu().contiguous().view(-1).view(__import__("torch").uint8).numpy().tobytes())
    return h.hexdigest()


def phase_config(config, phase):
    if phase not in {"hardware_preflight", "pilot"}:
        raise ValueError("Unknown focused training phase")
    if phase == "hardware_preflight":
        # Diagnostic instances do not consume training/validation/test seeds.
        from training.config import SeedRange
        return config.model_copy(update={"train_seeds": SeedRange(start=970000, count=1),
                                         "max_optimizer_steps": 1})
    return config


def run_session(config, runtime, output, *, bundle=None, sampler=None, diagnostic=False,
                phase="pilot", artifact_root=None, volume_attested=False):
    """Same trainer/save/reload/export path for the diagnostic and future target."""
    import torch
    from peft import LoraConfig, PeftModel, get_peft_model
    from transformers import TrainerCallback
    from trl import GRPOConfig, GRPOTrainer
    from training.adapter import JsonArenaRollout, RolloutLimits, native_reward

    verify_runtime(config, runtime)
    config = phase_config(config, phase)
    if diagnostic:
        if bundle is None or sampler is None:
            raise ValueError("Offline diagnostic requires explicit tiny-model fixtures")
    else:
        if artifact_root is None or not volume_attested:
            raise ValueError("Independently attested durable output volume required")
        blockers = config.blockers()
        if phase == "hardware_preflight":
            blockers = [x for x in blockers if x not in {
                "task_mix_unconfirmed", "target_gpu_smoke_unverified"}]
        if bundle is not None or sampler is not None or blockers:
            raise ValueError("Frozen confirmed target configuration required")
        if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
            raise ValueError("One CUDA GPU required")
        if not torch.cuda.is_bf16_supported():
            raise ValueError("BF16 support required")
        bundle = load_target(config)
    output.mkdir(parents=True, exist_ok=False)
    base, tokenizer = bundle
    base_for_reload = copy.deepcopy(base) if diagnostic else None
    model = get_peft_model(base, LoraConfig(r=4 if diagnostic else 16,
                                           lora_alpha=8 if diagnostic else 32, lora_dropout=0,
                                           target_modules="all-linear", task_type="CAUSAL_LM"))
    before = adapter_digest(model)
    deadline = time.monotonic() + config.max_wall_seconds

    class Deadline(TrainerCallback):
        def on_step_begin(self, args, state, control, **kwargs):
            if time.monotonic() >= deadline:
                raise TimeoutError("Local session deadline reached")

    rollout = JsonArenaRollout(tokenizer, RolloutLimits(
        max_steps=config.max_steps, completion_tokens=config.max_completion_tokens,
        context_tokens=config.max_context_tokens, temperature=config.temperature,
        thinking=config.thinking), deadline=deadline, sampler=sampler)
    trainer = GRPOTrainer(model=model, processing_class=tokenizer,
        reward_funcs=native_reward, rollout_func=rollout, train_dataset=dataset_for(config),
        callbacks=[Deadline()], args=GRPOConfig(
            output_dir=str(output / "trainer"), use_cpu=diagnostic, bf16=not diagnostic, fp16=False,
            max_steps=config.max_optimizer_steps, num_generations=config.num_generations,
            per_device_train_batch_size=1, gradient_accumulation_steps=config.num_generations,
            max_completion_length=config.max_completion_tokens,
            learning_rate=config.learning_rate, gradient_checkpointing=not diagnostic,
            optim="adamw_torch", beta=0, loss_type="dapo", report_to="none",
            save_strategy="no", logging_steps=1, disable_tqdm=True,
            remove_unused_columns=False, use_vllm=False))
    status, error = "completed", None
    try:
        trainer.train()
    except Exception as exc:
        status, error = "interrupted" if isinstance(exc, TimeoutError) else "failed", type(exc).__name__
    # Export recovery state on failure as well; never label it trained success.
    checkpoint = output / "checkpoint"
    trainer.save_model(str(checkpoint))
    tokenizer.save_pretrained(checkpoint)
    # Reload uses CPU RAM; avoid allocating a second base on the training GPU.
    if base_for_reload is None:
        base_for_reload, _ = load_target(config)
    loaded = PeftModel.from_pretrained(base_for_reload, checkpoint, local_files_only=True)
    equal = adapter_digest(model) == adapter_digest(loaded)
    if not equal:
        raise ValueError("Saved adapter reload differs")
    report = {"status": status, "phase": phase, "error_type": error, "diagnostic_fixture": diagnostic,
        "target_model_training": not diagnostic and trainer.state.global_step > 0,
        "optimizer_steps": trainer.state.global_step,
        "adapter_changed": before != adapter_digest(model), "reload_equal": equal,
        "audit": rollout.audit, "export": export_checkpoint(checkpoint, output / "checkpoint.tar.gz"),
        "provider_billing_stopped": None, "gpu_fit_verified": False,
        "limitation": "Private wrapper/proxy; GPU fit and provider billing are separate measured prerequisites."}
    if artifact_root is not None:
        from training.artifact_store import publish_archive
        report["mounted_export"] = publish_archive(output / "checkpoint.tar.gz",
            artifact_root, output.name, volume_attested=volume_attested)
        report["mounted_export"]["local_mount_fixture"] = diagnostic
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--validate-inputs", action="store_true")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--model-root", type=Path)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--phase", choices=["hardware_preflight", "pilot"], default="hardware_preflight")
    args = parser.parse_args(argv)
    if args.execute:
        # This precedes all file reads, environment credential lookups and model imports.
        raise SystemExit("Paid execution remains locked; no model loaded or provider contacted")
    if not all((args.config, args.runtime_root, args.model_root, args.artifact_root)):
        parser.error("--validate-inputs requires configuration and all mounted roots")
    from training.deployment import validate_session_inputs
    config = TrainingConfig.model_validate_json(args.config.read_text())
    report = validate_session_inputs(config, args.runtime_root, args.model_root, args.artifact_root)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
