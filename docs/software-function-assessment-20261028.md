# Software partial-credit MetaHarness assessment — 2026-10-28

Added a separate offline assessor for the frozen 32-assignment function-block screen. The existing binary terminal compatibility adapter cannot represent valid partial software repairs; this assessor retains their measured native semantic reward instead of rejecting them or coercing them to zero/one. It does not change either candidate, the comparison inputs, or any reviewed request.

It executes `scoreCell` from the existing unmodified MIT MetaHarness `fitness.mjs`, pinned to `ruvnet/metaharness@b8c3d38de41203faf633ef6dceb8452a4727b0ea` through the existing hash-checking compatibility module. This is actual offline fitness execution, not Darwin search, model optimization, training, or a Flywheel receipt.

## Scope and safeguards

- Requires all 32 assigned results, four samples per arm/task/seed, and the two frozen software tasks and two screen seeds. Checks result identity, prompt/problem hashes against screen inputs, and non-reused supplied call/response/reservation IDs.
- Scores eight same-prompt groups separately. Different procedural cases are never pooled to manufacture reward variation.
- Retains native partial credit and separates valid wrong/partial/full from format, edit rejection, execution, provider, budget and truncation failures. A failure with an observed native reward of one is projected as failure for analysis. Raw records remain unchanged.
- Preserves unknown finish reasons. Under upstream classification an invalid-format response with unknown termination is conservatively truncation, rather than inventing a normal stop.
- Reports full-rate and semantic-mean differences over all 16 assigned attempts per arm, with per-task/seed paired differences. Failed attempts remain in both denominators. These point estimates are not statistical confirmation. Four prompt groups across two procedural seeds are not 32 independent cases.
- Supplied identities/accounting are checked for consistency, not independently attested. The caller must authenticate archives and bind the exact frozen input digest before using this module. No provider implementation, paid-call admission, automatic selection, promotion, or submission is included.
- Confirmation scoring explicitly refuses execution until a separate attested input binding exists. It does not generate confirmation observations. Improvement and leaderboard flags remain false.

## Verification

Seven local Node tests passed using explicitly fictional results. They cover partial-credit signal, failure precedence, unknown termination, rejection breakdown, within-case grouping, all-attempt paired denominators, identity/coverage errors and refused confirmation. They execute the real pinned upstream fitness module. No saved private responses were used and no new model responses were generated.

Reproduce from the repository root:

```bash
node --test research/software-function-assessment-20261028/test_assess.mjs
```

The new files have not yet been tested inside ruOS. Work stayed offline after the fixed operating-hours stop. Fresh model screen and disjoint confirmation remain unexecuted. Native candidate tests from the prior step are separate evidence and do not validate this new assessor. No model or ranking improvement is claimed.
