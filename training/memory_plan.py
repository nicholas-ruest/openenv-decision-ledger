"""Shape-only target memory planning; no checkpoint weights or GPU are used."""
from __future__ import annotations

import torch
from accelerate import init_empty_weights
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForImageTextToText, Qwen3_5Config


def memory_plan(metadata: dict, index: dict, context_tokens: int = 16384):
    if metadata.get("model_type") != "qwen3_5" or not 128 <= context_tokens <= 16384:
        raise ValueError("Pinned target architecture and bounded context required")
    with init_empty_weights():
        base = AutoModelForImageTextToText.from_config(
            Qwen3_5Config.from_dict(metadata), dtype=torch.bfloat16,
            attn_implementation="eager")
        base_parameters = sum(p.numel() for p in base.parameters())
        model = get_peft_model(base, LoraConfig(r=16, lora_alpha=32, lora_dropout=0,
            target_modules="all-linear", task_type="CAUSAL_LM"))
    if not all(p.is_meta for p in model.parameters()):
        raise ValueError("Memory planner allocated a real model tensor")
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    text = metadata["text_config"]
    heads, vocab = text["num_attention_heads"], text["vocab_size"]
    full_layers = text["layer_types"].count("full_attention")
    kv_bytes = 2 * full_layers * text["num_key_value_heads"] * text["head_dim"] * context_tokens * 2
    return {"base_parameters_from_meta_architecture": base_parameters,
        "base_bf16_bytes_from_shapes": base_parameters * 2,
        "checkpoint_weight_bytes_advertised": int(index["metadata"]["total_size"]),
        "checkpoint_shards": len(set(index["weight_map"].values())),
        "lora_trainable_parameters": trainable,
        "lora_fp32_weights_gradients_adam_states_bytes_estimate": trainable * 16,
        "context_tokens": context_tokens,
        "one_fp32_eager_attention_matrix_bytes": heads * context_tokens ** 2 * 4,
        "one_fp32_full_vocabulary_logits_bytes": context_tokens * vocab * 4,
        "full_attention_kv_cache_bf16_bytes_one_rollout": kv_bytes,
        "real_model_tensors_allocated": False, "checkpoint_weights_downloaded": False,
        "gpu_fit_verified": False,
        "limitations": ["These are individual tensor estimates, not a measured peak or summed upper bound",
            "Additional activations, linear-attention states, temporary buffers and allocator overhead are excluded",
            "Generation is sampled sequentially; GRPO backward has independent memory requirements",
            "Eager attention and vocabulary logits make long-context hardware measurement necessary"]}
