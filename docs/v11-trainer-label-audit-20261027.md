# v11 public trainer label audit, 2026-10-27

Re-read the actual public run summary, raw logs, alerts and seven metric series for GlobalBusinessAdvisors/a3274296c46341a847407f97. The raw log API returns148 rows, optimizer steps1–148. Every one of1036 metric values matched its exact raw optimizer step. No task rotation was inferred. The dependency's public source was inspected at its declared Trackio0.40.0 wheel digest; the public training Space source is pinned at362671b590eb2536f86d86bd211b44f7af61bd04.

| Recorded numeric ID | Recorded updates | Zero-retry updates | Nonzero std+gradient | Reward1/std0 updates | First10 / last10 zero-retry reward |
|---|---:|---:|---:|---:|---|
|1|50|50|38|0|0.188929 /0.153571|
|2|49|48|38|10|0.650953 /0.864427|
|3|49|48|45|0|0.420833 /0.407500|

Training was active:121 of146 updates with zero recorded retries had nonzero recorded reward variation and gradients. Numeric group2 also had10 saturated zero-retry updates. These are training diagnostics, not private task solves or held-out improvement. A rise in group2's training reward does not explain which software family transferred; no family label is attested.

The actual raw logs contain numeric `step/task` and `step/tasks`, with timestamp as their only string-valued field. Summary configuration contains a task count but no task-ID map. The current ingestion source accepts finite numeric metrics and a small configuration allowlist that excludes task-name maps. This is evidence about the observed current source, NOT proof of which source revision ran historically. Four public alerts contain no software task identifiers or mapping fields. Their message bodies are not copied into public artifacts.

The four alert rows use step numbers65/133; positive retry metrics occur at optimizer steps66/134. No alert-to-task attribution or inferred offset is applied. Four alerts must not be counted as four independent failed training episodes, nor joined to task numbers at the same numeric alert step without a trainer-provided semantic rule.

Added an audit that checks raw log counts, exact metric joins and explicit labels. It accepts only an observed structured map/per-step label; a task list, task count or rotation never supplies names. Fourteen tests pass for missing/conflicting mappings, duplicate steps, missing metrics, changed values, unsafe source execution and alert-step ambiguity. It parses logging allowlists with AST literals without importing or executing the public server. The compact numeric fixtures reproduce all148 steps; no prompts, completions, alert bodies, credentials or account/billing data are published.

A bounded public collector reproduces the reads without any credential. The existing exact-step learning analyzer remains the source of per-ID statistics. Unknown names stay unknown, so these diagnostics do not authorize named-family weight changes. A narrow public-source/mapping question was sent to the already authorized Slack thread; no private results were included. No new inference, model training, request change, HF replacement or Arena submission occurred. ruOS was not accessed after its stop boundary.

Public sources:
- https://openenvarena-training.hf.space/?project=GlobalBusinessAdvisors&runs=a3274296c46341a847407f97
- https://huggingface.co/spaces/openenvarena/training/blob/362671b590eb2536f86d86bd211b44f7af61bd04/ingest.py
- https://pypi.org/project/trackio/0.40.0/

Next require an explicit run-bound task map before labeling these numeric groups. Independently continue the media trajectory assessor and preserve both reviewed candidates. These measurements do not establish software transfer or a new ranking.
