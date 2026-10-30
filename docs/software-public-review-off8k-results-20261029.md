# Computed public-example feedback versus neutral review: inconclusive, October 29

Execution source: `c2b281342baaf580323bc09005945606f2ea1712`. Eight attempts were frozen on one fresh procedural case, four per arm. Both arms required proposal/review/final, had identical first prompts and common settings, and used the unchanged complete Native contract and independent hidden grader. Only computed checks on the six already supplied public examples versus neutral review differed. Neither helper preservation nor explanatory compiler diagnostics was combined.

| Arm | Assigned | Recorded | Full solves | Other recorded outcomes | Uncalled |
|---|---:|---:|---:|---|---:|
| Neutral review | 4 | 3 | 1 | one partial (0.95); one candidate execution failure | 1 |
| Computed public-example feedback | 4 | 3 | 2 | one provider timeout with unknown usage | 1 |

The phase stopped when the next public-feedback call timed out after 360185 milliseconds. There were 11 actual calls and ten auditable replies. All observed replies were independently replayed against the pinned Native implementation; request, response identity, observed usage, budgets and classifications matched. All ten response identities and eleven call identities were distinct. All three supervisors verified clean shutdown before their deadlines.

The two usable public-feedback attempts received actual computed feedback. One proposal passed 5/6 visible examples and finished fully correct after revision; the other passed 6/6 and finished fully correct. These are descriptive trajectories, not a causal effect estimate: the incomplete controlled study cannot establish an improvement.

All eight original assignments remain explicit. The unknown-usage call retains its full reservation, and the last two assignments were not called. No retry, replacement, redraw or later chunk was launched. No full-rate effect estimate or complete four-sample MetaHarness group fitness is reported. Selection is false; confirmation case 2750000 remains unmaterialized.

Both arms requested thinking off, with actual provider thinking behavior unattested. Limits were unchanged: 8192 completion tokens including observations, 24576 context, first generation at most 6000, at most two calls, 600-second attempt wall and 1200-second worker supervision clipped to the operating stop. Maximum accounted completion was 2679 and maximum observed context 5911. No interpreter or resource difficulty was added.

Ten Native/scripted caller tests and ten assessment tests passed before live execution. Their log SHA256 values are `49e79f949846d34bc459f434084bd63c96f64971070d1c2a47415df2f0c362ad` and `6e059486093873f735d8ea5afba6c531cdcdbf927488f11dd5b514ac0a1d78f6`. They are protocol controls, not model solves. The assessment adapter uses the unmodified pinned MetaHarness fitness module only when its required data are available.

Private closure proof SHA256: `2fccae4bc0c4344f628d2364712858a6046f46642561f0d6a12c95ae88317d4a`. Raw trajectories, billing and account records remain private.

A separately qualified prospective candidate applies this same controlled intervention to the already existing joint task, `software_repair-ignore-d2`, at source `e2d7488092598a26fb7ee93874d9a62203495988`. Its controls passed, but it has no model calls or measured effect. It is not a retry of this phase.

No confirmed model improvement, Arena training transfer or leaderboard gain is established. No reviewed request, runtime image, HF dataset, spending cap or purchase changed, and no Arena POST occurred.
