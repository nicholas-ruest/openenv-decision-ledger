# Public-example self-tracing: screen did not confirm

This is a completed base-model inference comparison, not model training or an Arena result. The treatment asked the model to mentally trace all six supplied public examples; it did not execute tests or provide computed feedback. Helper preservation was not part of this intervention.

| Phase | Neutral review | Public-example self-tracing | Full-solve delta |
| --- | ---: | ---: | ---: |
| Frozen screen | 0/4 | 2/4 | +0.50 |
| Fresh disjoint confirmation | 1/4 | 1/4 | 0.00 |

The screen selection was frozen before confirmation observations were materialized. The confirmation failed the preregistered positive full-solve criterion. The selected screen and confirmation are not pooled into a gain estimate. No candidate promotion, software-transfer claim or leaderboard gain follows.

Both phases used SOFTWARE ignore-d3, one different procedural case per phase, Qwen/Qwen3.8-27B:deepinfra, temperature 0.7, thinking requested but not independently attested, generation maximum 4000, total completion including terminal observations 4096 and context 8192. Source/contract/examples/action schema were matched within phase. These local budgets differ from the reviewed v12/v14 resource profile (8192 completion / 24576 context), so these are not equivalent evaluations of those requests.

All eight assigned calls in each phase returned distinct actual response identities and known usage. Identities were checked disjoint across phases, and stored replies were independently replayed through the Native grader. No retries or discarded assignments. Confirmation categories: neutral review had one full, one partial, one execution failure and one truncation; self-tracing had one full, two partials and one execution failure. Confirmation mean semantic delta was +0.058333333333333404; this did not meet the full-solve selection criterion.

Screen source: `730102d5753eff01003cde189d9f42c2b648f00a`. Confirmation source: `58f5148cf01479db3349be5e18461d30da298196`. Screen input SHA256: `669253433c09c02f9e74ebe4b3ef6322df53d6da2b3cdf344e0c0a589d80344a`. Confirmation input SHA256: `9a940b9258619ae86885d0809b40f4eebe7086d2ad405c1c627e96c479cecff4`. Selection receipt SHA256: `769c61724e32fab92d803fc2d1ddc67e44fb4652f995410c5b9f87fd2f141d77`.

The actual pinned MetaHarness `fitness.mjs:scoreCell` at `b8c3d38de41203faf633ef6dceb8452a4727b0ea` scored the complete assigned groups. Both confirmation groups had signal 0 with execution/truncation outcomes preserved. This statistic is not a claim about a trained model's gradient. No Darwin runner was used. Source and tests are in `research/software-selfcheck8-20261029` and `research/software-selfcheck8-confirm-20261029`. Confirmation validation: seven Native caller tests and ten assessment tests passed, including rejection of a reused screen response identity. Private raw trajectories and billing remain private.
