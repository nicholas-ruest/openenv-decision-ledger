# Private training readiness

Status: CPU preparation preflight passed on October 12, 2026. No GPU rental, target model training or Arena submission authorized.

The native JSON-action adapter and locked preparation launcher now pass nine tests, a real TRL optimizer step on a tiny diagnostic model, and exact checkpoint save/reload. See [private training preflight](private-training-preflight.md) and [sanitized evidence](results/training-cpu-preflight-2026-10-12.json). The diagnostic uses scripted off-policy actions; it establishes software integration only. The target paid launcher, model loading, GPU memory and billing/rental cleanup remain unvalidated and locked.

Before launch, finish Darwin and select a fresh-seed-confirmed/Flywheel-approved candidate or document a no-improvement baseline decision. Freeze the source revision, public image digest, task mix, reward implementation, tokenizer, model checkpoint and inference settings. Anonymous native protocol replay must pass on that exact image.

Training signal must be measured by within-rollout-group reward variance, full solves per family/difficulty, invalid actions and truncation. The 29/32 easier-task calibration score does not by itself establish useful GRPO reward variation.

Prepare a stateful per-generation OpenEnv adapter for private GRPO. A LoRA pilot would be explicitly a proxy, not a claim of exact Arena replication. Trainer settings and memory compatibility require validation; the Arena guide's one-H200 allocation does not prove another 27B trainer fits on one GPU.

Before paying for a longer run, review the GPU quote and hard cap, then verify model loading, one rollout group, backward pass, checkpoint save and reload. The quote must specify GPU type/count, precision, tuning mode, rollout engine, context, storage, wall-time limit and cleanup behavior.

Evaluate base and trained checkpoints on the same untouched test seeds and identical inference settings. Keep training, checkpoint-selection validation and final-test seed manifests disjoint. Publish binary full-solve rates, per-domain results, provider failures and paired outcomes separately from partial training reward.

Existing spending authorization: USD50 total for inference/calibration. Separate GPU approval remains required. Arena submission is prohibited until the user reviews the exact request and gives explicit approval.

References: https://huggingface.co/docs/trl/openenv and https://huggingface.co/docs/trl/grpo_trainer . This document remains a target-training readiness plan. The locked CPU preparation launcher is tested; target 27B paid execution is not implemented or approved.

