# Frozen software screen caller — 2026-10-29

Implemented a manual one-shot caller for the existing 32-assignment function-block screen. It defaults to a plan and has no training, purchase, dataset-update or Arena-submission operation. Neither the treatments nor the frozen input schedule changed.

The caller checks the immutable input digest, both assignment schedules, sampling settings, and native reconstruction of every screen request. It uses the validated one-response Trial adapter. Confirmation observations remain ungenerated. No phase shrinking, repeated response consumption, resume, retry, or redraw is implemented.

The live path requires an externally completed, fresh private reconciliation using the existing audit format. It checks the complete audited receipt inventory and its file/ledger hashes, an attested carried prior, current billing observation and execution authorization. It then uses the existing DollarReservations implementation, complete-phase admission, selected-route quotation and pinned tokenizer. It never freshens a receipt or changes a cap. The existing allocation guards remain unchanged; this source grants no new financial authority.

The existing Linux supervisor bounds the worker to at most 1,200 seconds and the remaining time before the fixed stop. A killed worker leaves an incomplete durable archive, not a completed phase or an automatic restart. Local termination does not attest cancellation at a remote provider, and reservations are never refunded.

Before each call, an intent and reservation event are flushed. Private raw replies are credential-checked before storage. Actual response IDs are hashed for identity checks; client labels are explicitly local identities. Missing usage stays unknown. Terminal observations count toward the 4,096 completion budget, and canonical reconstructed context plus provider-reported usage are checked against 8,192. This is a direct-native proxy, not proof of equality with the Arena chat wrapper. Thinking and checkpoint equivalence remain unverified.

All assigned outcomes remain in the denominator on normal completion. A provider failure with unknown usage stops further admission; remaining jobs are recorded as uncalled budget failures without invented provider or reservation identities. The software assessor can retain these outcomes while withholding token-dependent fitness where usage is unavailable.

## Verification status

The default plan and Python compilation succeeded locally. Three local financial-guard tests passed with temporary, explicitly fictional receipt files. They cover complete-inventory checking, changed/omitted receipts, and denied authorization or unattested prior spending. They do not inspect or modify user accounts or ledgers.

Five scripted native integration tests were authored. A bounded ruOS command was issued against source `0c4b0c7fae9da5405279bed0ee4d1d97a44d3e7d`, but the command response, follow-up process/log read, and desktop status requests timed out. **The remote test outcome is unverified.** No duplicate test command was launched. A later local revision generalized receipt-inventory validation and added the pure guard tests; that revision also requires native validation. Check the existing process and archive before any further launch.

During permitted ruOS access, from a fresh checkout of the exact candidate source:

```bash
python -m unittest discover -s research/software-function-caller-20261029 -p 'test_*.py' -v
```

The scripted integration tests use native grading and the cached tokenizer with a scripted reference-response backend. They contain no real provider calls or actual fund reservations. Do not call them training or model solves.

No live phase was launched. Fresh model screen, disjoint confirmation and leaderboard improvement remain unmeasured. Private state synchronization is pending transport recovery. All reviewed requests, images and datasets remain unchanged.
