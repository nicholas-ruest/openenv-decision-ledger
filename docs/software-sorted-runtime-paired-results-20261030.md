# Shared-program sorted-call screen results, October 30, 2026

The fresh controlled screen **tied at 2/4 full solves in both interpreter versions**, with semantic mean 0.50 in each. Selection failed. Reserved disjoint confirmation 3010000 was not materialized.

Four actual model calls produced four known replies. Every returned program was graded by both isolated pinned Native interpreters, yielding eight Native grades. The same exact program bytes, task and cases were used in each pair. All requests, response identities, usage, Native outcomes and token accounting were independently replayed. This is four model generations, with cost counted once.

One program actually exercised the sorting extension: baseline rejected its sorted-call syntax; the candidate accepted it but then failed during execution. The patch therefore improved parsing for that program **without producing an additional solve**. The other failed program also remained an execution failure. There were no provider, budget, format or truncation failures in this screen, and no baseline full solve was lost.

Source: `31142aad48343ef10486916bc2ecb3ffaab334d1`; baseline interpreter `f0e43cea…b9932f`, candidate `be2672ea…a4e4a8`. One fresh procedural case at seed 3000000, four sampled programs, checked against 39 prior cases/102 input files. Maximum accounted context 7,658; maximum generation plus observation 4,885, within unchanged 24,576/8,192 limits. Observed generation tokens totalled 18,810. Both supervisors closed cleanly and all workers stopped.

The actual pinned MetaHarness `scoreCell` at `b8c3d38de41203faf633ef6dceb8452a4727b0ea` returned zero signal for both four-outcome groups: two semantic-eligible full solves and two Native execution failures. The classifier's infra bucket represents Native execution failures here, not provider outages. It does not establish GRPO productivity or model learning.

Separate posthoc diagnosis found an unsupported `bool()` call in the sorting-exposed failure, and a model `TypeError` in the other failure; supplied function names and arities were retained. Those findings are hypotheses for a new candidate, not revisions of this screen. The sorting result remains 2/4 versus 2/4.

No model, training, transfer or leaderboard improvement is claimed. No Arena POST, dataset replacement, production image replacement or reviewed v12 change occurred. See [frozen method and qualifications](software-sorted-runtime-paired-qualification-20261030.md).
