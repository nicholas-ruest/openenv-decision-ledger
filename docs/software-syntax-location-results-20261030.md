# Source syntax-location feedback: completed screen

Execution source `7ed888bfa18c41851ad6b94e22da0bb0cfc72c27` compared standard required review with source-only Python syntax-error location feedback. First prompts, action schemas, public-field feedback, parent-status reminder, interpreter, grader, request sampling and 8192/24576 accounting limits were identical.

| Arm | Assigned | Full | Partial | Wrong | Native execution |
|---|---:|---:|---:|---:|---:|
| Standard review | 4 | 0 | 1 | 1 | 2 |
| Syntax-location review | 4 | 0 | 1 | 0 | 3 |

All 16 requests returned independently replayed replies with known usage. All eight assigned attempts remain in the denominator, and all four bounded workers shut down cleanly. No provider, budget, format, edit-rejection or truncation failures occurred. Native execution failures remain failures; the upstream MetaHarness scorer's infrastructure category does not establish provider outages.

Full-solve delta was zero. Mean semantic reward across all assigned attempts was 0.191667 versus 0.204167 (delta +0.0125). Selection failed, and reserved confirmation was not materialized. Critically, none of the four treatment first proposals triggered the new syntax-error diagnostic. This screen provides no causal estimate of that diagnostic's effectiveness. The small partial-score difference cannot be attributed to it.

The exact source passed 28 native/protocol and 10 assessment tests before execution. A separate source-only replay exposed parser locations on two previously observed invalid first proposals; that replay made no model calls and is not a performance result. The live screen case was disjoint from 31 prior cases across 70 input files. One case and four samples per arm do not demonstrate transfer.

Actual pinned MetaHarness `fitness.mjs:scoreCell` at `b8c3d38de41203faf633ef6dceb8452a4727b0ea` scored both groups; signal was zero in both. Maximum accounted context was 6562; maximum generation plus observations was 3403. No retry, training, production image replacement, Arena POST, HF replacement, model improvement or leaderboard gain is claimed.
