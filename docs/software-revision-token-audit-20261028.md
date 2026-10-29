# Native software revision token diagnostic

Source: `5da062ee9e2533be1b692da03d61e1280aecb9b9`. Three unit tests passed on ruOS. A bounded run captured 96 actual in-process OpenEnv WebSocket trajectories across 48 public staged cases (two scripted paths each). A separate read of the saved native frames recomputed all 96 action/observation costs and checked identities and terminal results. No provider or model was called.

| Measurement | Maximum |
|---|---:|
| Serialized action JSON plus both complete post-reset observation frames | 2331 tokens |
| Reconstructed canonical JSON conversation | 5461 tokens |
| Terminal observation frame | 52 tokens |

No scripted trajectory exceeded 4096 completion or 8192 reconstructed context tokens, or the frozen v14 request's 8192/24576 limits. The reset affects context only; the terminal observation is included in completion. Data-only observation counts are retained separately in the private diagnostic. Both paths use reference source as a scripted control: wrong supplied module then reference revision, or reference module then retain it. These terminal full rewards are oracle controls, not model solves.

The cached tokenizer was hash-verified as `0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3`, with truncation/padding disabled. The native frame archive hash is `37fed5519ca727ba0cc52c1cd940f6cf1048b0cb15e44317294edda0377356ab`; raw trajectories remain on ruOS and are not posted publicly. The launch transport returned an availability error while the bounded child continued; the actual worker argv was inspected, no duplicate was launched, and its completed archive was verified after it exited. The initial verifier used system Python without tokenizers; rerunning the read-only verification in the existing training venv succeeded. No environment packages were changed.

This measures **serialized control payloads**, not Arena/provider token billing. Production system instructions, schema injection, chat-template overhead and model thinking are not attested. Reconstructed context is not a production context upper bound; real model responses may be longer or fail. This does not establish matched token budgets, model revision quality, training benefit or private transfer. Native source ran in the pinned detached checkout using the existing venv; it was not a new anonymous container qualification.

All frozen v12/v13/v14 requests and qualified images remain unchanged. No HF replacement, paid call, training, submission, new automation or public conversation post occurred. This result closes the terminal-observation diagnostic gap on the scripted paths; further control-count expansion is not evidence of improvement. The decisive missing evidence remains a fresh disjoint model comparison, which the current existing allocation has not admitted.
