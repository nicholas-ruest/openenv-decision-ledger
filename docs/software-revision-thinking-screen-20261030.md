# Revision-only thinking: positive screen, confirmation pending

The frozen screen produced **1/4 full solves with revision-only thinking versus 0/4 with thinking disabled**, a +0.25 full-solve difference and +0.0625 semantic mean difference. This passes the predeclared screen selection rule. **It is not yet a confirmed improvement or leaderboard gain.**

Execution source `50a17340714307559a802135eca4349c7cf6678e`; software-ignore-d2, seed 2860000. All eight assignments completed, all sixteen calls returned distinct usage-accounted replies, and every request, response, budget and native outcome was independently reconstructed. All workers shut down cleanly. No provider, format, execution, budget or truncation failure occurred in this screen.

| Arm | Full | Partial | Semantic mean |
|---|---:|---:|---:|
| Thinking disabled | 0/4 | 4 | 0.870833 |
| Thinking only on revision | 1/4 | 3 | 0.933333 |

Both first proposals disabled thinking. After identical public-example field feedback and the same parent-directory contract reminder, only the treatment's final revision enabled it. First prompts, action schema, native source/interpreter/grader, provider route, sampling and two-response limit were identical. Total completion-plus-observation budget stayed 8192; maximum observed was 7081. Context stayed below 24576; maximum observed was 9501.

The real pinned MetaHarness `fitness.mjs:scoreCell` at `b8c3d38de41203faf633ef6dceb8452a4727b0ea` scored both groups. Its descriptive signal was one in both groups; this is not the claimed benefit. The observed difference is the single additional full native solve.

Selection and all original artifacts are frozen before fresh confirmation. The reserved confirmation jobs use seed 2870000 and unchanged trial, sampling and native intervention. The separately tested confirmation-only adapter requires exact positive-screen evidence and rejects changed artifacts. Confirmation results will be reported separately without redesign, retries, redraws or pooling.

This is base-model inference calibration on one procedural screen case, with four stochastic attempts per arm. Arena sampling-wrapper equivalence is unverified. No training, transfer, promotion, Arena POST, HF replacement, runtime-image qualification, or leaderboard gain is claimed. Frozen v12 and rollback v11 remain unchanged.
