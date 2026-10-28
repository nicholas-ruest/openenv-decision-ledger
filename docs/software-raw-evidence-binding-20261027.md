# Raw software evidence binding, 2026-10-27

Added an offline binding layer between persisted job envelopes, actual saved requests/responses, the existing append-only reservation ledger, fresh native resets and the paired assessor's normalized record schema. No provider/launch/spend/refund operation exists in this module. Softwarev12 and mediav13 request/image bytes are unchanged.

For every saved job it checks arm/task/seed/sample and planned call identity, fresh actual request/reset/workspace hashes, single-call limit, matching reservation label/amount, unique response hashes, complete response/usage bounds, and replayed native reward. Rebuilt records must exactly equal the normalized archive in durable dispatch order. The paired assessor still requires a complete32-attempt phase and disjoint confirmation before directional evidence; a structurally valid partial archive cannot be called a full phase.

A reservation may exist without a returned response. That is recorded as a reservation-only attempt, distinct from both observed responses and unreserved attempts. Failure rewards remain excluded from semantic reward calculations but attempts stay in the denominator. No counters are reset or refunded.

The existing writer returns float(decimal reservation); comparison therefore checks that exact float projection, rather than requiring a rounded JSON float to equal arbitrary-precision ledger text. It does not use a broad tolerance. Nonfinite, negative and overflowed amounts are rejected.

Twenty offline tests pass, including lost-response reservations, unreserved budget failures, missing/duplicate ledger rows, amount/call/prompt/workspace/normalized-result drift, native replay mismatch, missing responses, over-reservation usage, truncated completions and duplicate/incomplete jobs. A separate offline legacy adapter is provided to exercise this binder against the already completed16-response archive with frozen source hashes; its actual revalidation result is recorded separately when run.

Limits: a legacy ledger has no timestamps and the runner records response metrics after receiving a reply. This layer cannot attest reservation chronology, an attempted dispatch that produced no reply, or cryptographic provider-response authenticity. It reports those claims false. Source/policy dependencies must be verified by the invoking adapter. No new live comparison, productive confirmation, training improvement or promotion is claimed.
