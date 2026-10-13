# Private training CPU preflight

Status on October 12, 2026: native adapter and a locked preparation launcher are
tested on CPU. The target 27B model has not been trained, loaded, or tested on a
GPU. Paid execution is disabled. This is preparation, not training readiness.

The adapter uses the unchanged native Decision Ledger environment and verifier,
with a fresh instance for every rollout. It executes JSON actions, appends native
observations, and passes TRL an `env_mask` that excludes observations and role
prefixes from the learning loss. Generated model tokens remain eligible. Invalid
actions and incomplete/token-limited episodes are reported separately and return
no reward to the trainer. Full solves require native reward 1.0.

Nine tests passed for native state isolation, observation masking, strict action
parsing, truncated episode handling, token limits, disjoint seed ranges, and source
drift rejection. An offline diagnostic used real TRL 1.6.0 and a tiny random GPT-2
model constructed from configuration, with no model download or inference call.
One optimizer step changed 16 parameter tensors; checkpoint save and reload were
exactly equal. The real Transformers generation path was separately exercised
with an eight-token limit and correctly reported truncation.

The backward-pass diagnostic uses scripted actions with native rewards
`[1, 0.75, 0, 1]`. These are explicitly off-policy test fixtures. Their rewards and
parameter changes do not establish trained policy improvement. They are never
used in hosted calibration or a paid training run.

The private adapter uses an explicit ChatML wrapper. This is a documented proxy
protocol, not verified equivalence to Arena's production chat wrapper. Thinking
mode prefills `<think>` and requires a completed `</think>` before parsing JSON.
Compatibility with the eventual pinned Qwen checkpoint still requires testing.

A second diagnostic now also passes with the target's advertised architecture,
`Qwen3_5ForConditionalGeneration`. The public Qwen3.8-27B metadata is pinned at
revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`; only its metadata was read.
The diagnostic constructs a tiny two-layer model with both linear and full
attention, applies LoRA r4/alpha8 to all linear modules, and executes the same
native adapter through real TRL. One optimizer step changed 15 parameter tensors,
and adapter checkpoint reload was exactly equal. The production GPU kernels,
27B weights, full-size memory footprint and actual target tokenizer were not
used in that diagnostic. Reference PyTorch attention kernels ran on CPU.

The provisional preparation configuration reserves disjoint train seeds
900000–900127, validation seeds 910000–910031, and final-test seeds 920000–920063.
It currently includes only software d2, sets `task_mix_confirmed=false`, records
the proposed public model revision and tokenizer hash, and leaves local target
checkpoint and GPU validation unset. The read-only plan
reports these blockers. `--execute` fails before loading a target model or
connecting to any service.

Run the CPU preflight from a checkout using a separate interpreter:

```bash
python3 -m venv /tmp/decision-ledger-training-venv
/tmp/decision-ledger-training-venv/bin/python -m pip install -r training/requirements-cpu.lock
export TRAINING_PYTHON=/tmp/decision-ledger-training-venv/bin/python
export TRAINING_SMOKE_OUTPUT=/tmp/decision-ledger-training-smoke-new
bash scripts/training-preflight.sh
```

Use a new smoke output directory. The launcher refuses to overwrite one. It runs
offline and disables implicit Hub-token use; no HF token is passed in arguments,
recorded in a report, or included in training arguments.

Before a paid pilot: finish Darwin confirmation and its signed Flywheel gate;
decide on a supported task mix or document the unchanged-baseline decision;
freeze the exact model/tokenizer and inference wrapper; then prepare the target
trainer configuration and a GPU quote for review. A reviewed hardware preflight
budget is needed to measure 27B model loading, memory, one rollout group,
backward pass and checkpoint reload. A CPU diagnostic cannot establish GPU fit.
The paid launcher, rental cleanup and billing-cap enforcement remain locked and
must be implemented and validated against the approved provider/quote.

References:

- TRL custom rollout contract: https://huggingface.co/docs/trl/v1.6.0/en/grpo_trainer
- TRL OpenEnv integration: https://huggingface.co/docs/trl/openenv
- Tested TRL release: https://pypi.org/project/trl/1.6.0/

No GPU rental, additional purchase, target model training, merge or Arena
submission is authorized by this preflight.
