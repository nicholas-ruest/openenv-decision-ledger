# Software output-contract screen — 2026-10-31

The fixed initial output-contract note failed selection: baseline **0/4 full solves**, treatment **0/4 full solves**. All eight assigned attempts ended in truncation; none produced a complete final action for Native semantic grading. These are truncation outcomes, not eight semantically wrong solutions.

| Arm | Assigned | Full | Truncation | Known provider replies |
| --- | ---: | ---: | ---: | ---: |
| standard_contract | 4 | 0 | 4 | 8 |
| explicit_contract | 4 | 0 | 4 | 8 |

This is one underlying joint software task with four paired samples and alternating arm order. The intervention added only a fixed initial reminder to return exactly the supplied entry paths. Original task, source, examples, schema, Native package, sampler, review behavior and budgets were held constant. First generation was capped at 6,000 tokens, total generation plus observations at 8,192, and context at 24,576. Maximum observed accounted context was 8,082; maximum completion plus observations was 8,096.

All 16 calls have independently verified request/response hashes and usage; all four finite workers shut down cleanly. Actual pinned MetaHarness `fitness.mjs:scoreCell` (revision `b8c3d38de41203faf633ef6dceb8452a4727b0ea`) classified four truncations per arm and no eligible solves. Semantic scores are unavailable for these final truncated actions; zero score contributions in the selection calculation do not imply Native wrong grades.

The prespecified positive-full-delta selection failed. The reserved disjoint confirmation case was not materialized. No promotion, training, new Arena evaluation, dataset replacement, or leaderboard improvement is claimed.

Source executed: `67d23ab24220fab022f2eb58bffc81d951b092c5`. Private assessment SHA-256: `241bc3499484808b3b62349e47d1c2411a5d1bcf7090599c9c530c188502a2bc`. Native task package was unchanged from `bc9a7fab8392c17a6f1d4bf27a6aa50c92df9ebb`.

A separate serialization-example intervention remains a separate study. This result does not test that intervention.
