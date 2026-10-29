# Supplied-helper preservation policy — 2026-10-27

Implemented `scripts/software-helper-policy.py` as an independent, process-local observation wrapper. It adds guidance to implement the missing function and prefer preserving supplied complete components. It still permits contract-required changes and alternate correct implementations. No output filter, grader change, repair insertion or reference-code injection is applied.

This responds to measured screen evidence: one actual .95 partial rewrote the supplied `rule_mode`; restoring that function in posthoc replay yields1. That is evidence of a possible avoidable error, not evidence the new guidance improves model performance.

## Actual validation

Eight policy tests passed: original observation unchanged, only prompt changes, both task targets, unknown/joint-task rejection, delegated step unchanged and wrapper restoration after injected failure. With the existing runner/assessment/archive/admission tests, **42 focused offline tests passed**.

Native ruOS manifest generation actually ran using the frozen runtime: two arms × two software prerequisites × two seeds in each phase. Only prompt text changed across arms; source files, hidden/public cases, workspace identities and examples matched. Screen and confirmation each contain two underlying cases, with **no case-hash overlap**. The saved native manifest SHA256 is `f8fa2146a64a197e6fe9e5fdd9d36fc86ba0f9088c32d06d23ea3335c224c789`. No model call was performed. These are protocol identity checks, not additional model solves.

The CLI rechecks frozen runtime dependency hashes, rejects existing output paths and asserts disjoint procedural case identities. Run offline:

```bash
python scripts/software-helper-policy.py \
  --runtime-root /path/to/frozen-runtime \
  --output /path/to/fresh-helper-policy-manifest.json
```

Use `environment_policy(base, arm)` only in a separate process for one arm, before BOTH reset capture and actual episode execution. Never change the module class while workers are active. This is research code, not a replacement Arena image. V12 reviewed source/request/image remain unchanged.

## Frozen future comparison

Screen: seeds2200000 and2200100. Confirmation:2210000 and2210100. Tasks:ignore-d3 andignore-d4. Four independent samples per arm/task/prompt require **32 calls per phase**; do not recycle the old16-call screen as an experimental baseline. There are four task/prompt groups per arm over two underlying cases, not32 unique tasks.

Keep runtime/provider/checkpoint route, thinking request, temperature.7, JSON mode,8192 generation and24576 context matched. Only the guidance differs. Freeze actual settings, selected provider metadata, source hashes, tokenizer, prompts and call identity before admitting calls. Interleave scheduling order or otherwise predeclare the order to avoid unacknowledged time/provider confounding; distinguish that from shared live module mutation.

Report full/partial/wrong and format/provider/truncation/execution/budget failures for every sample. Keep failures in denominators; report both arms' counts and prompt-group differences. Reject duplicate response/call identities, any workspace/case mismatch and confirmation leakage. The existing single-policy stage assessor's fixed seeds/settings cannot silently assess this two-arm protocol; a dedicated paired evidence assessor and controlled single-arm execution coordinator are still required before paid execution.

No inference phase was launched: fresh actual billing reconciliation and whole-phase admission under existing receipts/caps remain mandatory. No new allocation is created. Native validation is complete; model effect, fresh confirmation, training transfer and ranking improvement remain unestablished.

This code is not a new MetaHarness search or Flywheel promotion. Reviewed v12 is unchanged and unapproved; no HF replacement, training or Arena submission.
