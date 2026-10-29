# Live software probe and reliability correction — 2026-10-20

A real Qwen/Qwen3.8-27B:deepinfra probe sampled four independent rollouts of **one** merge-d3 prompt (seed 1082000), with thinking requested and JSON-object responses. Frozen source: 45f5c29. Result: one valid full solve, two TimeoutError failures, and one invalid action which copied the action schema. Reset/workspace hashes matched within the group, returned-call identities were independent, and the supervised worker completed and stopped. There were no valid partial or wrong answers. **The signal gate failed; there is no promotion, training or ranking claim.** See [the result](results/merge-live-signal-probe-2026-10-20.json). Raw redacted archives are preserved with hashes in that report.

The response wait was 90 seconds while an admitted call could request 4,096 generated tokens. At the route's advertised approximately 37 tokens/s, that allowance can exceed 110 seconds. This is a plausible contributor to the observed timeouts, not a proven causal explanation. The proxy response limit is now 180 seconds, clamped to the remaining stage deadline. The owned worker's hard deadline and cleanup remain mandatory.

The new reliability-only probe has a 600-second total worker bound, two independent samples, fresh seed 1086000, no retries, and unchanged accounting/provider/thinking/JSON settings. It uses the same existing private reservation ledger; no additional allocation or purchase is implied. Admission still refuses stale or insufficient reconciliation, and each call is reserved before sending.

The environment reset now supplies literal read/test/submit action instances and explicitly asks for an action rather than the schema. No answer, reference repair, hidden input, reward change, parser forgiveness or interpreter relaxation was added. The eight-task export remains provisional. This prompt change affects exported workspace hashes; prior packets and images remain separate.

The two-sample reliability probe cannot establish GRPO signal: the unchanged signal gate needs at least three valid samples with both a full solve and a non-full valid outcome. Four-sample, disjoint-prompt confirmation remains necessary before a training-signal claim. A fresh-seed before/after observation is descriptive, not a matched causal experiment; sample count, prompt and response limits differ. Checkpoint/thinking/Arena-wrapper equivalence remains unattested.

No Arena submission is authorized by this work. Human review of the final exact request is still required.
