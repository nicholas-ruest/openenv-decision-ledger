# Software transfer v11: review decision

Preparation completed on 2026-10-26. The worker exited, all three final component reports exist, and an independent verification checked every exported file hash, 672 distinct seeds and observations, disjoint train/validation/test splits (384/96/192), and 24,192 successful native reference checks. No candidate execution errors were reported. These are oracle controls, not model solves or new training.

The exact request is `config/software-transfer-v11-review-20261026.json`, SHA256 `9e747c343c609047ce5c3e891abb7e1db443fff604b160957cbb8b72f0d1388a`. It keeps the qualified164cb runtime and immutable77e34e46 image, with three equally rotated SOFTWARE tasks: dependency planning, transactions and ignore rules. No runtime change or new image is implied by this review commit.

This is an exploratory transfer hypothesis. The previous run finished132 updates and scored1/40, software0/5, delta−3 versus the untrained4/40 reference. Reward movement and nonzero gradients did not establish transfer. Earlier release/KV proxies often saturated; productive reward variance throughout the new mix remains unconfirmed. Hosted proxy/checkpoint equivalence is unattested, and trained weights are not available for a local paired evaluation.

The raw preparation report's minimum4/40 is BASE PARITY, not improvement. For this review, the success criterion for an improvement claim is at least5/40 overall AND at least1/5 software. A single noisy evaluation is insufficient to establish a reliable causal gain or promise any rank.

Status: ready for exact-request human review, NOT approved, submitted or trained. Matching HF dataset publication remains pending; the currently public48fe600d revision belongs to the previous run and must not be represented as this candidate. After explicit approval, publish only the six allowlisted artifact files plus the review metadata, verify their public hashes, then submit only the frozen request when admission is available. No automatic re-draw, permission expansion, new inference calls or paid training.
