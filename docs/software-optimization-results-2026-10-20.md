# Software optimization results — 2026-10-20

Two real Qwen proxy probes now replace speculation about the harder merge diagnostic. The [four-sample probe](results/merge-live-signal-probe-2026-10-20.json) produced one full solve, two response timeouts and one schema-copying invalid action. After adding concrete action examples and extending bounded response waits, a [fresh two-sample reliability probe](results/software-reliability-live-2026-10-20.json) produced one full solve and one HTTP error. Both used a single prompt per probe. They provide no valid partial/wrong-answer variance, causal reliability estimate or learning claim. Neither passed the signal gate. Both workers stopped; no Arena submission was made.

Source e40473c passed [CI39469848270](https://github.com/nicholas-ruest/openenv-decision-ledger/actions/runs/39469848270): 398 tests and 125 anonymous native WebSocket controls. Its public amd64 image is `ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:27c8c6c45b52669265472d322f47e393b8b7e2364cbf34e2205a4497eceea94e`. The 64-instance reset-guidance comparison found identical task specifications, labels, initial programs and non-README files; the README adds 159 UTF8 bytes. This image is a technical validation milestone, not a replacement for a human-approved submission packet.

## Curriculum correction

New diagnostic **software_repair-release-d2** retains release-d1's contract, independent oracle, three seeded semantic mutations and interpreter limits. It improves public examples for four behaviors: buildable-only test coverage, coverage-before-cost optimization, inclusive zero-budget handling, and lexicographic suite selection. A compound example and unknown-change control remain.

Across two fresh procedural cohorts (16 task instances, 576 reference checks), public tests detected **24/24** catalogued seeded defects in the new diagnostic versus **15/24** in the prior diagnostic. All **48/48** constructed proper partial repairs earned partial reward. Previously 10/48 earned zero and 7/48 already earned full reward because some seeded defects were not active in the sampled cases. There were no interpreter errors or within-cohort duplicate inputs, conflicting labels or public/hidden overlap. See [summary and reproduction command](results/release-witness-curriculum-2026-10-20.json) and raw cohort files beside it.

The new task stays outside the provisional eight-task export. These are constructed controls, not model actions or evidence of training gains. Live model sampling and fresh disjoint confirmation are still required. The new native replay adds actual WebSocket checks for single- and two-defect partial repairs; its CI outcome must be checked separately from e40473c above.

Future provider HTTP errors now preserve the status code without the response body, token or private error text. The archived HTTP failure predates that change; its status cannot be reconstructed or attributed to a particular cause.

No GPU rental, paid training, additional purchase, merge or Arena submission is performed by these changes.
