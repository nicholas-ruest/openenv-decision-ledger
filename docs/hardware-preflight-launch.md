# Software-only hardware preflight

The target worker is now wired through `training.hardware_preflight` and the
bounded controller `training.launch_preflight`. Both refuse execution without
an explicit, job-specific approval capability. The legacy `training.session
--execute` remains locked. No approval capability was issued during preparation.
The pilot phase is still unavailable through this controller.

## What was tested

On 2026-10-16, source `9f63d843739480bf41e4d07d6d16e356e9d2542e`
passed 67 offline tests with the existing CPU dependency lock. Mock HTTP tests
exercised creation, observed terminal state, deadline cancellation, ambiguous
creation responses and duplicate prevention. Request serialization matched the
installed Hugging Face Hub 2.2.0 SDK. No live Jobs mutation was made.

The approved-worker dispatch also completed a tiny Qwen hybrid LoRA optimizer
step, changed the adapter, saved it, reloaded it exactly and exported the archive
to a local mount fixture. These are scripted, off-policy CPU diagnostics. They
do not demonstrate target-model learning, GPU fit, or a ranking improvement.

## Concrete request to review before any spending

One H200 hardware preflight, software_change-d2 only, one optimizer step and
diagnostic seed 970000. The provider timeout is 3480 seconds including model
mount/startup; the session deadline is 3000 seconds. There is one attempt and
no automatic retry. At the proposed $5/hour quote, minute-rounded compute plus
two advisory startup minutes is $5. This is not an account-wide dollar cap;
recheck the provider quote, storage and taxes before requesting approval.

Use the newly built trainer image by digest after its CPU and anonymous-pull
checks pass. The earlier image does not contain this new controller. Model,
tokenizer, task and environment pins remain unchanged. No 27B weights were
downloaded during preparation.

## Operator procedure after explicit hardware-budget approval

1. Recheck the live hardware quote and exact approved allowance. Prepare an
   exclusive run ID, new input snapshot path and private durable launch-journal
   directory. An existing journal permanently prevents another POST for that ID.
2. Bind `Deployment` to the verified trainer image digest, pinned model revision,
   software configuration, input/output buckets and reviewed deadlines. Attest
   the actual mounted inputs/output only after their checks; set
   `gpu_budget_approved` only for the user's approved request.
3. Create a fresh, separate 32-byte approval key in the operator environment,
   never the HF credential. Set `OPENENV_PREFLIGHT_APPROVAL_KEY`. The signed
   envelope has exact fields `claims` and `signature`. Claims are
   `request_sha256` (canonical Deployment model_dump), `config_sha256`
   (canonical TrainingConfig model_dump), `run_id`, `phase=hardware_preflight`,
   `expires_at` (Unix time within two hours), and `max_compute_usd`.
   The signature is HMAC-SHA256 of canonical claims using the decoded hex key.
   `training.approval.canonical` and `digest` define the serialization.
   Do not issue a receipt for unapproved spending.
4. Stage and read back `deployment.json`, `training-config.json`, and
   `approval.json` in the exact read-only input bucket path. Compare all three
   bytes/digests before launching. The separate approval key travels only as a
   Jobs secret; it is never saved to the bucket, journal or argv. HF_TOKEN stays
   solely in the controller environment/HTTP Authorization header and is never
   passed into the worker.
5. Run `python -m training.launch_preflight --execute --deployment DEPLOYMENT
   --config CONFIG --approval RECEIPT --journal-root PRIVATE_EXISTING_DIRECTORY`.
   The controller sends one bounded POST, persists the returned job ID, and
   watches/cancels the existing job. Local approval files contain no HF token.
   Keep the controller supervised; provider timeout remains the backstop.
6. If creation is ambiguous, inspect Jobs for `openenv_run_id`; do not relaunch
   with another journal or run ID. Recover by monitoring the actual job ID.
   A lost response cannot be treated as a failed creation or verified stop.
7. Inspect the worker's durable `preflight-reports/RUN_ID.json`, adapter archive
   and hash receipt via an independent remote read. Confirm actual GPU memory,
   real generation, optimizer/reload, export and observed terminal job state.
   Controller terminal verification alone is not worker success or an invoice
   reconciliation. The worker's local write/read is not a remote durability proof.

## Remaining evidence

Cold model-mount timing, target 27B CUDA fit, actual remote checkpoint durability,
and real provider billing/termination require the separately approved hardware
preflight. Software training signal remains provisional. Hosted thinking/chat
wrapper equivalence to Arena is unattested. The failed Darwin candidate remains
unpromoted; this preparation does not alter environment/runtime reward code,
merge PR #2, start a pilot, or submit to Arena.
