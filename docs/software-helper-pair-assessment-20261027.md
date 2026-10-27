# Paired helper-policy evidence assessment — 2026-10-27

Implemented `scripts/assess-software-helper-pair.py` for the two-arm baseline versus supplied-helper-preservation comparison. It does not launch inference, train, submit or promote.

The old stage assessor has fixed single-policy seeds and cannot validate this experiment. The new assessor requires both arms, all32 expected samples, frozen runtime/settings, and each arm's exact prompt/reset hashes from the native manifest. It checks matched workspace/case identities, distinct underlying cases, unique call labels and observed provider-response identities. Failed attempts remain in the full-repair denominator; their recorded reward is never relabeled a semantic wrong answer.

Each of four task/prompt groups reports both arms' valid/full/partial/wrong counts, format/provider/truncation/execution/budget failures, conditional valid reward mean/std and full-rate difference over all four attempted samples. The overall difference is the mean prompt-group difference. With only TWO underlying cases, this is not32 independent tasks or a well-powered statistical result.

Confirmation is recalculated from both complete raw normalized record sets, not a supplied summary. It rejects shared case, prompt, call and response identities across screen/confirmation. A positive direction in both phases is reported descriptively only: no statistical-significance, trained-policy-gain or promotion claim.

## Actual checks

**20 new synthetic evidence-corruption/denominator tests passed;62 focused tests passed overall.** Tests cover missing/duplicate samples, runtime/settings/reset/prompt/workspace/case mismatch, duplicated call/response IDs, Boolean sample IDs, NaN reward, unobserved valid response, unknown failure class, and screen/confirmation leakage.

Updated native manifest generation to record arm-specific reset hashes. Actual ruOS generation completed with no model calls. Screen seeds2200000/2200100 and confirmation2210000/2210100 yielded matching across-arm cases/workspaces and disjoint phase case hashes. Saved updated native manifest SHA256:
`537f34dc57b7da9829106d9c8d9250e04874d5dbee3bad411902ea8007909e8c`.

Example offline assessment:

```bash
python scripts/assess-software-helper-pair.py \
  --manifest screen-manifest.json \
  --records normalized-paired-records.jsonl \
  --runtime-source 0b8ccc3ca70a67fed5fc5837b69022261cc60497 \
  --settings-sha256 FROZEN_SETTINGS_SHA256
```

Pass the selected phase object from the generated two-phase manifest. Records require arm/task/seed/sample, runtime/settings/case/workspace/reset/prompt hashes, client call label, observed-call Boolean, response-ID hash, failure class and reward. A unique client label is not proof that a call occurred. Separately verify raw actual requests/responses and their reservation links before interpreting a result; the report explicitly retains `raw_evidence_attestation_required:true`. This assessor verifies consistency, not authenticity of caller-provided archives/manifests.

## Remaining execution work

Implement a bounded coordinator using separate single-arm processes so the observation wrapper is never mutated while workers are active. Freeze ordering, settings and archives; collect actual raw records and normalize against each arm's preflight capture. Test cancellation/no-retry and append-before-call accounting. Whole-phase admission and fresh actual billing reconciliation are mandatory; no calls are launched by this change, no new allocation is created, and no old sample is recycled.

The reviewed v12 request/image/runtime, existing HF dataset and rollback are unchanged. No new training, submission, model effect, ranking improvement, MetaHarness search or Flywheel promotion is claimed.
