# Bool-on-sorted shared-program screen: no additional full solve

Four fresh model programs were each replayed unchanged in both isolated pinned Native runtimes. Bool support recovered an execution failure to a 0.95 partial solve. Full solves stayed **1/4 in both runtimes**, so the pre-registered selection gate failed. Reserved confirmation remains unmaterialized.

| Result | Sorted baseline | Bool candidate |
|---|---:|---:|
| Full | 1/4 | 1/4 |
| Partial | 2/4 | 3/4 |
| Native execution failure | 1/4 | 0/4 |
| Mean semantic reward, all assigned | 0.725 | 0.9625 |

There was one actual compatibility exposure and no lost baseline full solve. All four provider responses, request identities, usage counts, prompts and both Native grades were independently verified. No provider, format or truncation failures occurred. Generation cost is counted once per program, across eight Native grades. All inference supervisors and children stopped cleanly.

The pinned MetaHarness classifier changed its descriptive signal from 0 to 1 and eligible outcomes from three to four. That reflects the recovered Native execution failure on this one case; it establishes neither model learning nor measured held-out improvement. The full-solve selection rule was not relaxed to follow the semantic increase.

Frozen comparison source: `e834c57a7dd16e43771755e047ee6d20bdaaebe3`.
Native baseline: `34ae9401ec3a9530e2a71916060ea3a4c75eaa72`.
Native candidate: `bc9a7fab8392c17a6f1d4bf27a6aa50c92df9ebb`.

Actual generation was 18,927 tokens total; maximum context 7,711; maximum generation plus observations 4,941 per assigned program. Configured limits remained 8,192 generation plus observations and 24,576 context.

The candidate Native regression completed with 717 passes, one previously observed supervision-test failure, and 14 passing subtests. Deployment remains unqualified. Frozen v12, its image, the dataset and Arena submission state were not changed. No model, GRPO, transfer or leaderboard gain is claimed.
