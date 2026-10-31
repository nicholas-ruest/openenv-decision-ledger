# Final function-block revision policy: frozen candidate

A completed control attempt in the preceding study truncated its final rewrite inside the unchanged 8192-token generation-plus-observation budget. This separate candidate allows a final response to replace named functions instead of retransmitting a complete module. It has no fresh model result yet.

**Final source:** `8de6b520b342c1595dfae003cfe5e6d87114d8de`.

## Intervention and execution

Both arms use the same action schema, first prompt, source, public examples, public-field and public-runtime feedback, Native interpreter, provider route, sampler and total budgets. Both can submit complete modules or final function blocks. Only treatment review advice encourages localized function-block revisions. This evaluates the revision policy rather than comparing different first prompts or restricting the control's available edits.

A nonempty function revision supplies named top-level function definitions and the `revision_base_sha256` shown in the preceding feedback. The environment verifies that hash against the current public module, replaces only the named functions, and permits new helpers. Other code is retained. It consults neither reference implementations nor hidden cases while applying edits. Invalid hashes, ambiguous or malformed blocks and existing source-byte limits fail closed; an invalid edit never receives credit for a retained good proposal. Full-module replacement remains available, and empty content retains the current module.

Model code continues to execute only in the bounded Native interpreter. The complete Native package is byte-identical in both arms to `bc9a7fab8392c17a6f1d4bf27a6aa50c92df9ebb`. The action guide was aligned with the new schema before any paid execution. A cold-import check also caught an inherited module path that could resolve the wrong assessor; it was fixed and covered by a fresh-process test. Earlier unexecuted preparations are retained, and the planned case and input payloads were not redrawn.

## Qualification

**22 Native/protocol/transport tests passed**, including a one-helper repair that recovers a public runtime error, unchanged unedited code, stale-hash rejection, no credit on invalid revisions, actual HTTP/WebSocket schema and function-block payloads, independent request/usage/Native replay, real exposure recomputation, unknown usage, truncation and financial denial. **10 assessment tests passed**; the final source was checked byte-for-byte against those tested assessment files.

Native/protocol transcript SHA256: `42ff0ee64354a4d8337f7ce8166dfc6461e5a57613391850bb74875d0bd37629`.
Assessment transcript SHA256: `bc14f2f61c5bdab0e2503ccb5f43d21d6d18cf4fbecea0d040194b2ffca71450`.
Financial gate SHA256: `5e2f25daea0f59c248ab75e22a134b89259c6892d24335f3c9c4a1b807da7e8c`.

The shared Native package's broader suite has 717 passes, 14 passing subtests and one previously observed supervision-test failure, also present in the baseline. That failure remains unresolved; no production image is qualified.

## Token audit limits

A separate posthoc audit of one saved program compared an equivalent whole-module correction with its changed-function representation. Native AST fingerprints and public grades agreed. The serialized whole-module action used **1030 tokens**, and the function action including its hash used **264**. Both fit the 2985-token remainder in that particular replay.

The original provider response reported 4620 completion tokens, while its returned content measured 1019 tokens and its separate reasoning field measured 3599. This establishes that retransmitted code is only part of the cost. Function blocks may save output tokens; they are not a demonstrated fix for reasoning-related truncation. The audit made no model calls and is not a new solve or performance gain.

## Frozen fresh screen

Screen seed 3060000 is disjoint by source/examples from 42 prior cases in 110 input artifacts. Four samples per arm are assigned, with at most two responses each. Reserved confirmation seed 3070000 is unmaterialized. First generation is capped at 6000; generation plus observations at 8192; context at 24576. Provider defaults, temperature 0.7 and the absence of thinking overrides are unchanged.

Selection requires all eight assigned attempts, independent identity/request/usage/Native verification, no provider or budget failures, a positive full-solve delta, nonnegative semantic delta and at least one actually applied treatment function revision. Every failure remains in the original denominator. Fresh disjoint confirmation is required, with no redesign after selection.

No model learning, Arena-managed GRPO, transfer or leaderboard gain is claimed. Frozen v12, its image and the dataset are unchanged. This prepared comparison is separate from the completed public-runtime feedback study, whose selection failed because no diagnostic was exposed.
