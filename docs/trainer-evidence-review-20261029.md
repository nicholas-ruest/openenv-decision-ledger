# Named-task trainer evidence review — 2026-10-29

Inspected public `benchflow-ai/posttrainarena` revision `4fffddff36d8c321bce5cab0d3b4a8d270f277e9`, dated 2026-09-30. This is source evidence, not an attestation of the trainer revision or artifacts used by any particular Arena run.

The pinned [GRPO implementation](https://github.com/benchflow-ai/posttrainarena/blob/4fffddff36d8c321bce5cab0d3b4a8d270f277e9/pipelines/benchflow-task-posttrain/src/posttrainarena/benchflow_pipeline/grpo.py) constructs a per-rollout record with an explicit named task, training step, group identifier, reward and retry attempt. It saves individual records as `rollout.json` and includes the collected records in the `rollouts` array of the generated `train_metrics.json`.

Its group diagnostic checks that all samples in a group have one task name and one step, checks completeness against the configured generation count, and distinguishes constant-reward from varying-reward groups. This identifies a concrete artifact format to look for when named-task diagnostics are missing from dashboard metrics. It is not evidence that this exact format exists for the target run.

The pinned [pipeline implementation](https://github.com/benchflow-ai/posttrainarena/blob/4fffddff36d8c321bce5cab0d3b4a8d270f277e9/pipelines/benchflow-task-posttrain/src/posttrainarena/benchflow_pipeline/pipeline.py) reads the merged GRPO model's `train_metrics.json`; its final summary omits the detailed group rows. A summary alone therefore may not recover the required task-level observations.

Next evidence needed is the actual run-bound trainer manifest/revision and its original named rollout or detailed group records, if retained and accessible. Verify their provenance and step domain before any join to Trackio. Do not infer task names from dataset order, numeric task rotation, matching step numbers alone, or this unrelated public snapshot. Do not replace actual records with synthetic fixtures.

Public Hub source/artifact pages were unavailable through the retrieval service during this review. No run-specific artifact was recovered. The existing numeric-to-named task mapping remains unattested, so no per-family curriculum reweighting is supported by this review. No model calls, tests, training, candidate modifications or improvement claims occurred. No private records or account details are included here.
