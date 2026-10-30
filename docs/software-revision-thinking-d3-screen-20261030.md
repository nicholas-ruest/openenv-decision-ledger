# Revision-only thinking on ignore-d3: positive screen, confirmation pending

Execution source `715c0d8f5854e920343eb5f09e208c7b2a97394c` completed all eight assigned attempts and 16 actual calls. All usage, request/response identities, replayed native outcomes and clean worker shutdowns were independently verified.

| Arm | Assigned | Full | Partial | Native execution | Mean semantic reward, all assigned |
|---|---:|---:|---:|---:|---:|
| Thinking off | 4 | 1 | 1 | 2 | 0.470833 |
| Revision-only thinking | 4 | 4 | 0 | 0 | 1.000000 |

Full-solve delta was +0.75; semantic mean delta was +0.529167. The frozen positive selection rule passed. This is one procedural case with four samples per arm; it is not a confirmed improvement on unseen cases, training gain, or leaderboard gain. The originally reserved disjoint confirmation is reported separately. Earlier interrupted ignore-d2 confirmation remains closed and inconclusive; these results are not pooled with it.

Both arms used identical first prompts and content-only action schema, public-field feedback, parent-status reminder, route/model/temperature, native source/interpreter/grader and 8192/24576 total accounting limits. Both first proposals disabled thinking; only treatment revisions enabled it. All four treatment revisions returned a nonempty reasoning field; the other twelve replies did not. No reasoning text is published. Maximum accounted context was 9551; maximum generation plus observations was 6844. No provider, budget, format or truncation failures occurred. Native execution failures remain failures in the assigned denominator.

The 12 implementation and test files exactly match the earlier revision-thinking method under the declared research-path/namespace, existing task d2-to-d3 and procedural-seed/scope transformations. Native controls passed 18 tests plus 10 assessment tests on the execution source. The source/examples case is disjoint from 32 prior cases across 74 preserved input files. Actual pinned MetaHarness `fitness.mjs:scoreCell` at `b8c3d38de41203faf633ef6dceb8452a4727b0ea` scored both groups; its signal labels are not an effect estimate.

Selection is frozen in a 32-artifact screen gate with SHA256 `8b99e0797c0450e99b789da940316b5beffa44a8d838d050f7a26c20b397dde1`. The confirmation adapter must validate every artifact hash, independently recompute the original frozen selection, preserve trial/sampling methods and use the reserved case without redesign. No Arena POST, HF replacement, runtime-image replacement or production thinking-override support is claimed. Frozen v12 and rollback v11 remain unchanged.
