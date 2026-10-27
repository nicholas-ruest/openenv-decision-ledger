# Staged software curriculum v12 — review only

## Exact proposed change

Replace the three-family v11 mix with three equally interleaved tasks in one SOFTWARE family:

1. `software_repair-ignore-d3`: implement classifier aggregation with rule matching supplied.
2. `software_repair-ignore-d4`: implement rule matching with aggregation supplied.
3. `software_repair-ignore-d2`: implement both, retaining joint-task rehearsal.

The labels d3/d4 identify prerequisite scaffolds, not harder levels. Task ordering rotates; this is not an adaptive or temporal curriculum. Same one-code-action schema, independent oracle, semantic reward, interpreter/resource limits and 8192 completion / 24576 context token budgets. No format bonuses or artificial execution failures.

## Why test this

The previous joint task has a measured function-dependency plateau: fixing either whole function alone earned zero across eight fresh native fixtures, while fixing both earned one. The two scaffolds remove that cross-function dependency. All 56 controlled wrong semantic implementations earned partial credit without interpreter errors, and visible examples detected each tested defect. These are oracle edits, not model rollouts. Some incorrect repairs still earn .95, so saturation remains a risk. This is a transfer hypothesis; no model variance or held-out gain is confirmed.

## Frozen image and validation

Runtime source: `0b8ccc3ca70a67fed5fc5837b69022261cc60497`.

Public tested image: `ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:9455e57ef88fe99d94a0f0b32651c1f52472f9aba6da68c11a68db18c936ed22`.

[CI 40471693914](https://github.com/nicholas-ruest/openenv-decision-ledger/actions/runs/40471693914) passed all three jobs, 638 tests and 260 anonymous direct controls, including eight strictly fractional stage controls through the native WebSocket API. The old v11 image remains a rollback; its request and current HF dataset are not replaced by this preparation.

## Fixtures and approval

The reproducible packet builder produces separate train/validation/test procedural fixture exports and a deterministic source archive, with six allowlisted publication files. It makes no inference, publishing or submission calls. The runtime uses fresh generated episodes, not these exported rows. Fixture rows are explicitly not captured native reset observations.

Reference controls validate the environment; they do not measure the model. No trained weights are available for a local matched comparison. Arena's actual reference comparison is the held-out test. Improvement requires at least 5/40 overall AND at least 1/5 software; 4/40 only matches the untrained reference. One draw is noisy and top-ten placement is not promised.

The exact proposed request is `config/software-staged-v12-review-20261027.json`. It is UNAPPROVED and unsubmitted. Explicit human approval is required before replacing the HF dataset or posting to Arena. No purchases, GPU rental or paid standalone training are proposed. Any separate paid calibration still requires existing spend reconciliation.

## Completed packet controls

672 unique fixtures and hidden suites; 24,192 reference checks passed with no execution errors. Splits: 384 train, 96 validation, 192 test. All six publication file hashes verified; all 19 archived runtime/build files match frozen public source. 33 local packet/semantic/analyzer tests passed. Request SHA256: `afcd5e2f0d72eb164d6ed9b97ee715c045af17ef2e0db4d5cfab490201857648`. These are native oracle controls, not model solves.
