# Source-only diagnostic screen with common thinking-off request, October 29

Execution source: `a79db0100a9ca068d416c49f3953444d2e988422`. All eight assigned attempts completed on procedural case 2720000, four per arm, with 16 actual calls and 16 auditable replies. Independent Native replay verified assignments, exact requests, identities, usage, budgets and grades. There were no provider, budget, format or truncation failures.

| Arm | Full | Partial | Wrong | Candidate execution failure |
|---|---:|---:|---:|---:|
| Generic computed public feedback | 2/4 | 0 | 1 | 1 |
| Same feedback plus source diagnostics when applicable | 3/4 | 1 (0.95) | 0 | 0 |

The frozen full-solve selection delta is +0.25; semantic mean delta is +0.4875. **No actual treatment proposal triggered a compiler diagnostic.** Therefore this selected screen alone cannot attribute the difference to the diagnostic feature. Sampling noise is a plausible explanation. No improvement, training transfer or leaderboard gain is established.

Both arms required proposal/review/final, had identical first prompts, compiler, accepted language, full-contract grader, examples and model settings. Only bounded source-only compiler detail could differ after a rejected proposal. No helper-preservation intervention was combined. Both requested `enable_thinking=False`; actual provider thinking behavior remains unattested. Limits stayed 8192 completion tokens including observations, 24576 context, first generation at most 6000, at most two calls, 600-second attempt wall and 1200-second worker supervision.

The complete screen was scored using the unmodified pinned MetaHarness `fitness.mjs:scoreCell`. The candidate group had signal 1 with four eligible attempts; the generic group had signal 0 with three eligible attempts. The software adapter projects a candidate execution failure into the upstream environment-failure category, so that upstream category is not a claim of a provider or infrastructure outage. Native failure categories remain explicit.

Before model calls, 16 Native/scripted caller/diagnostic tests and ten assessment tests passed on the pinned source. Log SHA256 values are `a70a9f61630532fa2d33cee10207ab3e8097e1d85e0b89879d59d63fa9ea760c` and `095d991ceebe1e4855b7e761d231c5d31257b0aa794d8870a1487dac7a2b9e3e`. These controls are not model solves.

The immutable positive-selection receipt SHA256 is `fe11bd4ba23e4c31c2555e0273334dfa2cd52a30987638a76c8fe213ca7be5fb`. It binds all four actual input, record and event hashes, all actual response identities, the exact source and common profile. It was frozen before confirmation case 2730000 was first materialized. That confirmation uses unchanged code/settings and distinct response identities; its outcome must be evaluated independently without pooling the selected screen.

The preceding thinking-requested diagnostic phase `d18440e73c16a1f795b4fb161510ecda24fce60e` stopped on its first provider call after 360037 ms, with zero usable replies or diagnostic exposure, seven uncalled assignments and one retained unknown-usage reservation. Its closure proof SHA256 is `f9ec223ae02abd44d596914710d0ae612b3b92e42aee20e3eab2d2a7ccc36315`. The separate common-profile study is not a retry or an estimate of thinking-mode effects.

No reviewed request, runtime image, dataset, spending cap, purchase or Arena submission changed. Private raw trajectories, receipts and account data remain private.
