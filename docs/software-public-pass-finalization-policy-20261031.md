# Public-pass finalization policy prototype — 2026-10-31

Implemented a separate offline controller policy over the original Native Trial, following the [posthoc diagnosis](software-first-proposal-finalization-diagnosis-20261031.md). It is **not a live caller, training environment, or measured candidate**.

Both arms have identical initial messages. Baseline permits the original second model response. Treatment invokes the original empty action only when the first, normally completed model response produces an explicit public-only review with all public examples passing. The public-only decision happens before ordinary Native hidden grading. A failing public review preserves the second model response.

Controller actions are recorded separately from model responses and contribute zero generated model tokens. The policy returns every new Native observation: treatment may produce both review and final observations from one model response. The helper counts both observations; a future live caller must enforce that sum within the original generation-plus-observation limit. **The old live caller must not be reused unchanged**, because its last-observation-only accounting is incompatible with this controller behavior.

Four focused Native controls passed: identical initial prompts and original terminal grading, second-model-response preservation after public failure, refusal to recover truncated/provider-failed responses, and unchanged format failure. They also checked separate controller attribution, both-observation accounting, and refusal of any request or action after terminal finalization. Four original diagnostic controls were rechecked. These are trusted controls on the previously materialized qualification case, not model samples or fresh-case evaluations.

The existing Native package, schema/parser, financial gate and generation/context limits were not modified. Planned screen 3120000 and reserved confirmation 3130000 remain unmaterialized. The full matched protocol, independent live replay/accounting, case inventory, source leases, current private reconciliation and admission are still pending. Managed-actor portability remains unattested. No new provider calls, spending, training, image build, Arena submission or HF replacement occurred.

ruOS was observed stopped/asleep during this preparation and was left untouched. Its previous durable-storage blocker and pending private-state synchronization were not represented as freshly resolved. The previous model results and frozen v12 request remain unchanged.
