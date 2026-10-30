# Public-example review with provider-default sampling: confirmation failed

Public review solved 3/4 versus neutral review's 0/4 in the frozen screen. On the reserved disjoint confirmation it solved **1/4 versus 2/4**, and mean semantic reward was **0.25 versus 0.9375** (difference −0.6875). The frozen confirmation criteria failed. This method is not promoted and does not establish improvement.

| Phase | Neutral full | Public review full | Neutral failures/partials | Public review failures/partials |
|---|---:|---:|---|---|
| Screen | 0/4 | 3/4 | 3 Native execution, 1 truncation | 1 truncation |
| Disjoint confirmation | 2/4 | 1/4 | 2 partial (0.833333, 0.916667) | 3 Native execution |

All eight assigned attempts in each phase remain in the denominator. All 32 provider replies were independently replayed, with fresh request/reply identities verified across the screen and confirmation. Every bounded worker closed cleanly. No provider/budget failures, retries or redraws occurred in these phases. Confirmation used a source/example bundle disjoint from 35 earlier cases across 86 input archives. Two procedural cases and four stochastic samples per arm per phase are a small, adaptive research result; they do not establish broad software transfer.

Both arms share the same first prompt, content-only action schema, public-contract reminder, generic review advice, provider route, sampling and two-response budget. Only the treatment receives computed feedback on the six supplied examples. No thinking override is supplied on either turn; all 32 actual replies carried nonempty reasoning fields. This observes this provider route, not Arena's private actor configuration. The unchanged aggregate generation-plus-observation/context bounds were 8192/24576; measured maxima were screen 8096/8038 and confirmation 8083/7646. The research first-generation allocation remained 6000; production wrapper equivalence is unverified.

The screen's posthoc first-proposal replay found one control proposal regressed from full to execution failure, while two treatment proposals improved from wrong/partial to full and one stayed full. These are diagnostics on existing responses, not extra fresh solves. In confirmation, one treatment first proposal passed all six public examples yet its final revision failed execution. Public-example success alone must not be counted as a hidden solve.

The actual pinned MetaHarness fitness module b8c3d38de41203faf633ef6dceb8452a4727b0ea was executed. On the confirmation group it scored signal 1 for neutral review (four eligible mixed semantic outcomes) and 0 for public review (one eligible outcome). This is the module's offline group metric, not observed GRPO productivity. Its conservative upstream infra bucket includes the three Native program-execution failures; these were not provider outages. Native failure categories remain separately reported.

Screen source: 33c0c708e823bd42ae9de8150c025c78d5c8fe5b. Confirmation source: ec20188b06dacc8eb48976628f36901b1a78ea6a. The exact 33-artifact admission inventory was verified before confirmation materialization. [Sanitized results and evidence digests](software-public-review-default-results-20261030.json). [Screen record](software-public-review-default-screen-20261030.md).

The separate empty-action-finalization candidate changes the termination/prompt contract and must be measured independently; it does not inherit the screen result. The earlier revision-only-thinking result remains separate. No production image, frozen v12 request, dataset or Arena submission changed. No managed training ran, and no leaderboard gain is claimed.
