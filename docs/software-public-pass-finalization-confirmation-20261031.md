# Public-pass finalization did not pass disjoint confirmation

The completed fresh confirmation returned **0/4 full outcomes in both arms, with all eight attempts truncated**. The screen advantage did not reproduce. This candidate is not promoted, and no model improvement, training improvement or leaderboard gain is established.

| Phase | Procedural cases | Draws per arm | Baseline full | Treatment full | Treatment controller-assisted full | Actual calls / known replies |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Screen | 1 | 4 | 0/4 | 2/4 | 2 | 14 / 14 |
| Disjoint confirmation | 1 | 4 | 0/4 | 0/4 | 0 | 16 / 16 |

Both arms received identical initial Native prompts, schemas, supplied source/examples and sampling. Baseline used the original two-response review protocol. Treatment finalized the first proposal through the original empty action only when an explicit public-only review reported all public examples passing. That decision preceded hidden grading. Otherwise treatment used the original revision response. Controller actions were separately recorded with zero generated tokens; both Native observations consumed the original budget. No method or sampler change occurred between phases.

Confirmation source was frozen at `b4c07d4b13eef904806a8ea26ca41cee8d6478d0`. The positive-screen gate verified the complete immutable original artifact inventory, recomputed the pinned assessment and checked unchanged Trial/controller/sampling code before confirmation materialization. The reserved confirmation case had 36 distinct inputs with zero overlap against 1,548 previously used distinct inputs across 47 task/seed pairs. Four draws of one case are not four independent procedural cases.

All four confirmation chunks passed independent Native replay, original reply/call identity checks, token accounting and clean shutdown checks. Maximum accounted context was 8,353; maximum generation plus observations was 8,096, within the unchanged 24,576 and 8,192 limits. First-generation cap remained 6,000. All original assignments, including truncations, remain in the denominator. There were no provider, execution, format or budget errors in the recorded final confirmation categories.

The actual pinned MetaHarness module `fitness.mjs:scoreCell` at `b8c3d38de41203faf633ef6dceb8452a4727b0ea` scored both confirmation groups with signal 0 and eligible count 0. These calibration/controller-policy studies did not run GRPO and do not establish productive training groups. Managed Arena actor equivalence remains unverified. Frozen v12 and the HF dataset were not revised; no Arena submission occurred.

The aggregate result is in `research/software-public-pass-confirmation-20261031/result-20261031.json`. Original prompts, responses, cases, traces and account records remain private.

## Separate helper-preservation follow-up

The public task contract explicitly identifies two supplied helpers as complete. A separate source-only preservation prototype passed three targeted Native tests on an already-used qualification case. It retains actual model text in the transcript, labels transformed actions as controller-authored, and exposes controller receipts for budget accounting. It does not combine public-pass finalization with helper preservation.

A posthoc public-only replay of all eight confirmation first proposals transformed seven proposals. Six had comparable public-field reviews: two improved, none regressed, and none passed all public fields either before or after preservation. Two proposals were rejected in both versions and remain in the eight-proposal denominator. No hidden final grading was performed. This is diagnostic evidence from existing responses, not new model attempts, confirmation or improvement.

See `docs/software-helper-preservation-controller-20261031.md`, the prototype source/tests, and `posthoc_public_review.py` for reproduction. A matched live helper-preservation comparison remains unprepared and unadmitted. No positive performance claim follows from its scripted controls or posthoc public-field changes.
