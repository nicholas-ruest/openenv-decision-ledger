# Private training readiness

Status: preparation resumed October 14, 2026 with a software_change-d2-only pilot. Multi-category balance is not required for this pilot. Offline cohort validation passed all224 native positive/empty controls across128 training,32 validation and64 untouched test instances, with deterministic resets and no public-input collisions. These are oracle controls, not model solves. Focused signal confirmation and production launcher preparation continue.

Darwin finished with failed baseline confirmation and no promotion receipt; retain the existing runtime. The earlier confirmation plan was structurally underpowered (8 paired blocks versus13 required at candidateBudget7). Do not restart that recipe or weaken its gate. A focused pilot readiness screen is separate from environment-knob promotion.

CPU preparation preflight passed on October 12, 2026. No GPU rental, target model training or Arena submission authorized.

The native JSON-action adapter and locked preparation launcher now pass nine tests, real TRL optimizer steps on tiny GPT-2 and target-family Qwen3.5/LoRA diagnostic models, and exact checkpoint save/reload. See [private training preflight](private-training-preflight.md), [generic CPU evidence](results/training-cpu-preflight-2026-10-12.json), and [target-architecture CPU evidence](results/qwen-architecture-cpu-preflight-2026-10-12.json). These diagnostics use scripted off-policy actions; they establish software integration only. The target paid launcher, 27B model loading, GPU memory and billing/rental cleanup remain unvalidated and locked.

Before launch, finish Darwin and select a fresh-seed-confirmed/Flywheel-approved candidate or document a no-improvement baseline decision. Freeze the source revision, public image digest, task mix, reward implementation, tokenizer, model checkpoint and inference settings. Anonymous native protocol replay must pass on that exact image.

Training signal must be measured by within-rollout-group reward variance, full solves per family/difficulty, invalid actions and truncation. The 29/32 easier-task calibration score does not by itself establish useful GRPO reward variation.

Prepare a stateful per-generation OpenEnv adapter for private GRPO. A LoRA pilot would be explicitly a proxy, not a claim of exact Arena replication. Trainer settings and memory compatibility require validation; the Arena guide's one-H200 allocation does not prove another 27B trainer fits on one GPU.

Before paying for a longer run, review the GPU quote and hard cap, then verify model loading, one rollout group, backward pass, checkpoint save and reload. The quote must specify GPU type/count, precision, tuning mode, rollout engine, context, storage, wall-time limit and cleanup behavior.

Evaluate base and trained checkpoints on the same untouched test seeds and identical inference settings. Keep training, checkpoint-selection validation and final-test seed manifests disjoint. Publish binary full-solve rates, per-domain results, provider failures and paired outcomes separately from partial training reward.

Existing spending authorization: USD50 total for inference/calibration. Separate GPU approval remains required. Arena submission is prohibited until the user reviews the exact request and gives explicit approval.

References: https://huggingface.co/docs/trl/openenv and https://huggingface.co/docs/trl/grpo_trainer . This document remains a target-training readiness plan. The locked CPU preparation launcher is tested; target 27B paid execution is not implemented or approved.

