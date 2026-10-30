# Revision-only thinking request: frozen comparison

Execution source `50a17340714307559a802135eca4349c7cf6678e`; 18 native/protocol tests and 10 assessment tests passed before any model execution.

Both arms use the same first prompt, content-only action schema, native source/task/grading, public-field review and parent-directory contract reminder. Both first proposals request thinking disabled. Only the treatment's revision, after it sees public feedback, requests `enable_thinking=true`; the control revision requests false. Requested behavior must be checked from actual reply metadata. No reasoning text belongs in public artifacts.

The existing total completion-plus-observation budget remains 8192, context 24576, first proposal limit 6000, and final allowance is the unchanged remaining-budget calculation. Two responses, no retries/redraws, same provider route and sampling. This tests reasoning placement within a fixed total allowance, not more inference tokens. Arena wrapper equivalence remains unverified.

Four samples per arm on frozen screen seed 2860000; confirmation seed 2870000 is reserved and unmaterialized. First prompts match exactly; the source/examples are disjoint from all 62 inventoried prior input files (29 distinct cases, including prepared but unobserved cases). No observed cases are replaced.

All eight assignments remain in the denominator. Selection requires complete independent request/reply/native reconstruction, known usage, no provider or budget failure, positive full-solve difference and nonnegative semantic difference. Fresh disjoint confirmation is required before an improvement claim. No pooling with other studies.

Native log SHA256 `997c368e4855400c468b3a630737a13c34c8875dd7ea4a0b2d1730a295b0ba70`; assessment log SHA256 `4bcbd23f6f69728c5f119442d770775ebc40be4553e1646b62771ff8f875754b`. Shared reservation gate remains SHA256 `5e2f25daea0f59c248ab75e22a134b89259c6892d24335f3c9c4a1b807da7e8c`.

These are scripted qualifications, not model performance. This document does not admit paid calls, authorize Arena POST or HF replacement, qualify a runtime image, or claim training/leaderboard progress. Fresh private accounting and worker checks remain mandatory.
