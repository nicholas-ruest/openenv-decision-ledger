# Software optimization completion — 2026-10-20

[Final validation](results/software-optimization-validation-2026-10-20.json) records the immutable source/image, measured outcomes and limits. Source `7c3b6fcabaa32ddf784b7d692959a5019e6b802e` passed [CI39472423640](https://github.com/nicholas-ruest/openenv-decision-ledger/actions/runs/39472423640): **423 tests, 134 anonymous native WebSocket controls, and SDK validation**. Four WebSocket controls specifically verify genuine partial semantic repairs.

Public amd64 image: `ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:5fde5f1e675fa3c22a1a93cdefd8903d4b23629e5e10ab4630487345d74cf0c2`.

Six actual Qwen proxy rollouts covered two distinct prompts: two valid full solves, two response timeouts, one schema-copying invalid action, and one HTTP error. All valid completions were full solves, so training signal remains unconfirmed. No new model training or Arena submission occurred. Details and curriculum changes are in [the optimization report](software-optimization-results-2026-10-20.md).

The new release-d2 diagnostic improves sampled public defect detection from 15/24 to 24/24. All 48 constructed proper partial repairs earn partial reward, without execution failures or within-cohort duplicate/overlapping inputs. The contract, oracle, initial mutation procedure and limits are unchanged. Raw procedural audit cohorts are public beside the summary; these are controls, not model solves. The diagnostic stays outside the eight-task export.

The [next calibration plan](results/release-witness-calibration-plan-2026-10-20.json) is review-only and locked: eight independent samples across two fresh prompts, followed by eight conditional confirmation samples across two further prompts. Both screen groups and both confirmation groups must each contain at least three valid responses, one full solve and one valid non-full reward. Private admission and refreezing after an authorized unlock remain necessary. No automatic paid queue or Arena POST exists.
