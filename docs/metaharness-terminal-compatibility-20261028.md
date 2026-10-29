# Pinned MetaHarness terminal compatibility, 2026-10-28

This executes applicable scoring functions from actual MetaHarness, without running Darwin search, a provider evaluator, training, a promotion gate or submission. The unchanged MIT upstream fitness.mjs and confirm.mjs are attributed to RuvNet and pinned to [ruvnet/metaharness@b8c3d38de41203faf633ef6dceb8452a4727b0ea](https://github.com/ruvnet/metaharness/tree/b8c3d38de41203faf633ef6dceb8452a4727b0ea). The public pinned files were retrieved and compared byte-for-byte with the local source. Their SHA256 values are checked before importing:

- fitness.mjs: 852da62a33b833bc0a8cbc015891e3030d769b40fa41bf9793da84bdadfff130
- confirm.mjs: fd765ce849bbf5c75925da7427464a96f8d70f43b24308d9802f287a861dd81d

The two files and upstream MIT license are preserved unmodified under research/metaharness-compatibility-20261028/upstream. Our adapter contains only the contract translation and grouping checks; it does not claim to be an upstream search or training run.

## Measured compatibility findings

1. Upstream classifyEpisode checks reward1 before checking failure. In our terminal protocol an action-budget auto-grade can carry observed native reward1 while remaining a budget failure. Directly passing that record would classify it as solved. The adapter keeps the original category/native observed reward in metadata and projects failures to analysis-only reward0 with an ineligible failure code. It never rewrites raw/native grading or calls this a semantic wrong answer.
2. Upstream scoreCell evaluates random groups from a cell distribution. Our current requirement is variation within exactly the same case/prompt. Pooling solved-only prompts with wrong-only prompts can produce positive pooled signal while every same-case group has zero signal. The adapter therefore requires four complete groups of four independent samples with fixed task/family/seed/reset+workspace identity, unique observed call/response/reservation identities and no phase mixing, then invokes actual scoreCell separately for each group.
The MetaHarness signal is deliberately stricter than the custom media assessor's valid-outcome-variation flag: a four-sample group containing a failure has zero MetaHarness all-eligible-group signal even if its remaining valid samples include both0and1. This adapter does not replace or silently redefine the existing protocol assessor.

3. All five native failure classes remain ineligible. Format maps the auditor's known stop-terminated invalid-action fact into the upstream format classifier without inventing token usage or IDs; the recorded generation total supplies accounting. Provider/execution/budget classes can map to upstream infra, while the original five-way breakdown remains explicit. Binary media rejects fractional semantic rewards.
4. Upstream pairedOutcomes is designed for changed genome cells and consecutive four-seed blocks. This terminal plan uses repeated samples of the same case and nonconsecutive family-matched inputs. No direct confirmation/promotion equivalence is asserted. A small demonstration executes actual confirmationPower, explicitly marked unapplied to our protocol; it is not a model experiment or a confirmation receipt.

Nine new local compatibility tests passed. Separately,15 existing upstream fitness tests passed locally from the pinned source; those use upstream's already-public fixtures. The new CI workflow runs the9 compatibility tests and verifies the imported source hashes. [CI40670671637](https://github.com/nicholas-ruest/openenv-decision-ledger/actions/runs/40670671637), source fbf7c8766bb214e41120bb1fc9ef697744474da5, passed the9 new compatibility tests using the actual hash-pinned upstream modules. The15 upstream tests were a separate local run, not additional CI tests.

## Limits

Every new fixture is synthetic, including the counterexamples. Results establish contract compatibility, not task difficulty, model learning, an effect estimate or ranking improvement. The adapter expects already-audited normalized records; it cannot authenticate provider responses or turn invented records into measured evidence. It exposes no admission token, new allocation, provider driver or submission path. Softwarev12/media-v13 requests and images remain unchanged and unapproved. No new model calls, training, dataset replacement, Darwin run or Flywheel promotion occurred.
