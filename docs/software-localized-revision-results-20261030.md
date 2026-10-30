# Localized revision advice: completed negative screen

Execution source `9abe7dcfa8c13862c44a0b3db53dd2304c2611b6` compared full-module revision advice with literal-edit advice. Both arms accepted either representation and used identical first prompts, action schema, public-field feedback, parent-status reminder, native interpreter and grader. Only the second-turn advice differed. Thinking was disabled in both requests of both arms.

| Arm | Assigned | Full solves | Partial | Native execution | Mean semantic reward (all assigned) |
|---|---:|---:|---:|---:|---:|
| Full-module advice | 4 | 0 | 3 | 1 | 0.645833 |
| Literal-edit advice | 4 | 0 | 3 | 1 | 0.629167 |

Full-solve delta was zero; semantic mean delta was -0.016667. The preregistered selection rule failed. The reserved disjoint confirmation was not materialized. No model improvement, training benefit or leaderboard gain is claimed.

All eight assigned attempts remain in the denominator. All 16 actual requests and replies had known generation usage and independently replayed native outcomes. Every bounded worker shut down cleanly on the same boot. No provider, budget, format, edit-rejection or truncation failures occurred. The two native execution failures remain failures; the pinned MetaHarness scorer's `infra` category does not establish provider outages.

The treatment used literal replacements in two of four final answers (one replacement and four replacements); the other two used the accepted full-module fallback. Thus the advice produced real edit-format exposure without imposing an artificial format restriction. Maximum accounted context was 6587 tokens; maximum generation plus observations was 3440, within the unchanged 24576/8192 limits.

The one procedural screen case had source/example hashes disjoint from 30 prior cases across 66 preserved input files. Four samples per arm on one case do not demonstrate transfer. An analysis-only replay of the first two pairs found one treatment final answer passed all six supplied examples while remaining a native partial; public-example success was not relabeled as a full solve.

Actual pinned MetaHarness `fitness.mjs:scoreCell` at `b8c3d38de41203faf633ef6dceb8452a4727b0ea` scored both groups; signal was zero in both. Qualification passed 24 native/protocol and 10 assessment tests before paid execution. The earlier zero-call preparation was superseded before any reservation; frozen inputs were unchanged. No retries, Arena POST, HF replacement or runtime-image replacement occurred.
