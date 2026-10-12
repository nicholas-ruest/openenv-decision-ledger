# Decision Ledger
An OpenEnv Arena entry by Nick Ruest, built on Reuven Cohen's MetaHarness.
Eight procedural domains, independent reference solvers, bounded virtual-file tools, and an evidence-driven Darwin/Flywheel improvement loop.

## Runtime
Python/OpenEnv is the Arena protocol adapter. MetaHarness TypeScript is the development-time optimization layer. The submitted container requires no secrets, external model endpoint, database or GPU.
Actions list files, read bounded virtual records, and submit one answer. A fully correct answer earns 1; any incomplete or incorrect answer earns 0.

## Task coverage
Software dependency/test planning; industrial scheduling; sensor calibration; office reconciliation; finance ledger reconstruction; graph routing; security triage; media timeline verification. Three difficulty levels per family give 24 candidate cells, not 24 independent capabilities.
The initial candidate uses eight difficulty-2 train tasks. Darwin changes difficulty/token budget one parameter at a time. The final task manifest will be selected only after real target-model calibration.

## Improvement loop
1. Validate the runtime and reward controls.
2. Measure target-model rollouts with the Arena thinking configuration.
3. Use pinned MetaHarness Darwin to search candidate settings.
4. Re-measure baseline and winner on fresh disjoint seeds.
5. Use Flywheel's signed confirmation gate to reject unsupported promotions.
6. Publish the tested immutable image and public task dataset.
7. Show Nick the exact request and wait for explicit approval.

No scheduled or automatic submissions are enabled. No paid GPU is provisioned by these scripts. Oracle correctness and dry-run optimizer reports are not model-learning or leaderboard results.

## Run
See [build and validation](scripts/validate.sh), [Darwin runner](scripts/darwin.sh), and [architecture decisions](docs/adr/0001-arena-boundaries.md).
Use Python 3.12 and Node >=22.15. Clone with --recurse-submodules.
The GitHub Actions workflow tests, builds linux/amd64, publishes to GHCR, and replays the anonymously pulled digest in a separate job.

## Status
Not submitted. No official score. Public publication and target-model calibration must pass before review.
See [attribution](THIRD_PARTY.md) and [provenance](config/provenance.json).
