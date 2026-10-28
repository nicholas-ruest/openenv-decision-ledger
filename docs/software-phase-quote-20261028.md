# Pure software comparison quote

This helper computes a conservative upper-bound quote for the published 32-attempt, two-response, zero-retry research protocol. It bounds 64 independent calls at 8192 prompt tokens each and 131072 generated tokens in total (32 x 4096), with a 10% margin. It does not reserve, call a provider, select an allocation or grant execution authority.

The read-only public HF router model catalog on October 28, 2026 advertised Qwen/Qwen3.8-27B on deepinfra at USD0.20 input and USD2.50 output per million tokens. Applying those prices to the frozen protocol yields USD0.47579136 for one complete phase. An equal-size confirmation phase requires its own fresh quote and admission.

This is not expected spend, a new financial cap, or proof of production token parity. Post-reset observations consume part of the shared completion budget but are conservatively not deducted from the output bound. Model responses and hidden-case outcomes are not predicted by this arithmetic. A failed affordability check never shrinks the sample or reuses responses across arms.

Three tests passed locally and on ruOS, covering complete shared-output arithmetic, insufficient fictional remaining allocation, and invalid or changed inputs. Remaining-allocation values in tests are fictional examples only. No new inference, training, HF replacement or Arena submission was performed by this helper. No new automation was added. Private accounts and reconciliation are outside this published artifact.
