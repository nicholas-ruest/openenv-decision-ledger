# Replay diagnostic: future calibration plan

Status: review plan only. No inference has been launched or authorized by this
document. The diagnostic remains outside the default eight-task export.

The offline audit establishes that independent single-bug repairs can earn
partial reward on replay-d3. It does not establish that a model will generate
these repairs, produce useful within-prompt variance or improve after training.

## Frozen comparison

Compare replay-d2 and replay-d3 in one frozen source checkout, without changing
the interpreter, action schema, instruction wrapper, reward formula, model,
tokenizer, provider, thinking mode, temperature or episode limits between arms.
Freeze exact source-file hashes, selected-model advertised metadata and the
DeepInfra route before admitting any call. Arena checkpoint, thinking and chat
wrapper equivalence remains unattested.

| Stage | Tasks | Seeds per task | Independent samples per prompt | Rollouts |
| --- | --- | --- | --- | --- |
| Screen | replay-d2, replay-d3 | 1060000, 1060100 | 4 | 16 |
| Conditional confirmation | replay-d2, replay-d3 | 1061000, 1061100 | 4 | 16 |

These seeds are disjoint from the offline audits and existing train/validation/
test partitions. Each stage has four distinct task prompts, not sixteen.
Samples within each group must have identical reset/workspace hashes and
distinct complete request labels and provider-response identities. Different
arms have different case distributions and workspace text; they are not
identical-prompt causal comparisons.

Use the existing frozen limits: temperature0.7, thinking on, JSON actions,
maximum12 actions,8192 episode generation/observation units,16384 context units,
no retries. Record actual protocol values rather than inferring them from this
plan. The present screen script has fixed task groups: configuring and testing
the new groups is still required before any execution.

## Admission and decision

Execution requires a fresh private reconciliation of actual inference usage and
every linked reservation ledger, the existing shared allocation with its
original counters, and an explicit bounded wall deadline. Do not create a new
allocation, reset counters or spend during the current offline continuation.
If the complete predeclared screen cannot fit the remaining reconciled cap,
do not silently reduce the groups or treat an incomplete screen as evidence.

Analyze each arm separately with the version2 identity/grader checks. A
productive group requires at least three valid completions, a full solve and
a genuine non-full valid outcome. Provider, schema, truncation, execution and
budget failures cannot supply reward variance. Record full, partial and valid
wrong completions separately from every failure category.

Only run the predeclared fresh confirmation after replay-d3 produces genuine
screen signal. Require replay-d3 to pass the same gate on disjoint confirmation
prompts, with matched settings and disjoint call identities. A passing gate
supports a provisional single-family training pilot; it does not prove a
causal advantage over replay-d2, trained improvement or a leaderboard gain.
If both arms saturate or failures dominate, retain the existing mix and report
the negative result. No automatic training, promotion or Arena submission.
