# Public-example runtime source feedback: frozen candidate

This intervention adds source locations for bounded Native execution errors observed on the supplied public examples. It is separate from parser diagnostics, helper-retention advice and thinking controls. It has no measured model result yet.

The source-only prototype is `cba5105c87a13aaf9f7bd1f7126b28be923f8e6e`. Final controlled-comparison source is **`5cf4137e24b4c12610c0094f6b8426e4781a40f8`**.

## Behavior

Both arms receive identical first prompts, action schema, task, public examples, Native interpreter, provider route, sampler and total token budgets. Both have the existing public-field feedback and revision advice. Only the treatment adds `source_diagnostic` after a nonterminal public-field check.

The diagnostic runs the submitted program through a subclass of the pinned bounded Native interpreter on at most eight supplied public cases. It records only the first failing expression's source line, UTF-8 byte column, AST node type, bounded call identifier and exception class, plus the public-example index. It never reads hidden cases or emits arguments, expected/actual values or exception text. It does not patch global Native classes, execute model code as host Python or change terminal grading.

Native outputs, error types and interpreter step counts are unchanged in parity controls. A compile rejection receives no runtime diagnostic. Expression state resets per case. An observed saved program's invalid `range()` call was located using public examples alone; this posthoc diagnostic reproduction is not a new model solve.

## Qualification and controlled screen

**22 Native/protocol/transport tests passed**, including actual HTTP/WebSocket schema and completion behavior, matched first prompts, nonterminal reward zero, no first-proposal hidden grading, independent replay, usage tamper rejection, unknown usage retention, truncation and financial denial. **10 assessment tests passed**. The entire Native package is byte-identical to `bc9a7fab8392c17a6f1d4bf27a6aa50c92df9ebb` in both arms, including task descriptions. A stale inherited description was caught before materialization or paid execution; the final source carries the exact package.

Native/protocol test transcript SHA256: `178156852ffe97657fe82014fb83f070a60e7dd23edd64c6bea96161a8ff1a65`.
Assessment test transcript SHA256: `82a645941bd86ff0b41e04efe188e1d11b79f08329e28878286a621d160bd20a`.
The identical assessment implementation was tested before the task-description carry and verified unchanged afterwards.

The frozen screen has four samples per arm on one case, seed 3040000, disjoint by source/examples from 41 prior cases in 106 input artifacts. Reserved confirmation seed 3050000 is unmaterialized. Each attempt has at most two responses, a 6000 first-generation limit, an 8192 generation-plus-observation limit and 24576 context limit. Provider defaults and temperature 0.7 are unchanged; no thinking override. Every assigned attempt remains in the denominator, including execution, provider, format, budget and truncation failures.

Selection requires complete independently verified identities, requests and actual usage, no provider or budget failure, a positive full-solve delta, nonnegative semantic delta and actual treatment diagnostic exposure. Fresh disjoint confirmation is required before any improvement claim, with no candidate redesign after selection.

The shared Native package's broader suite completed with 717 passes and one previously observed supervision-test failure, also present in the baseline. That failure remains unresolved. No production image, Arena wrapper equivalence, GRPO result, transfer or leaderboard gain is established. Frozen v12, dataset and runtime image remain unchanged.
