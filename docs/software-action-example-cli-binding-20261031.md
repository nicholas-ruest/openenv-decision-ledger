# Exact CLI case-audit binding and clean-checkout refusal, October 31, 2026

A clean-checkout CLI check caught an argument-name mismatch before worker startup: the parser exposed --case_audit while the caller invocation used --case-audit. Argparse's default prefix matching could consume the latter as a prefix of --case-audit-sha256, leaving the actual path unset. The initial attempt stopped on missing explicit arguments; no phase, backend, account or provider was reached.

Source `b464b8a99c83419f57da014c743f37095e0e6bd0` fixes the interface. The canonical --case-audit path and --case-audit-sha256 digest now bind separately. The explicit legacy --case_audit alias remains supported. Implicit option abbreviations are disabled. Three targeted parsing tests passed in 0.003 seconds; log SHA256 `e8a72547d17cb7bef0be53424b43e4c5add413ddc41e89187cde01f184034843`.

The fixed commit was fetched into a new detached clean worktree and the real CLI was exercised locally with immutable original screen inputs, dummy nonexistent receipt/audit paths, no HF_TOKEN, and the existing public pinned tokenizer. The source's case-inventory lease remained None. The direct gate refused it, and the actual supervised CLI worker failed closed with shutdown verified and no phase archive or receipt created. The worktree remained clean.

[Machine-readable local refusal proof](../research/software-action-example-20261030/cli-refusal-proof-20261031.json), SHA256 `bc02b8947bad3829e5209affda0f031a72b05fef513fb3a634dcf114b532ae46`. Supervision-log SHA256 `cfcf0848a44733a81e3998e714bff1bcfde29995a3a04ebfefff532febdbef22`.

The CLI retains the existing supervisor-report convention: its shell process exited zero while the structured result was worker_failed. Qualification and admission must inspect that structured status, shutdown proof and actual artifacts; shell exit alone is not a successful phase. No model or selection record was manufactured.

No Native/grader, sampler, budget, financial gate, source inventory seal, environment or confirmation policy changed. No old failure artifact was reused or overwritten. The source remains unadmitted for paid execution.

The fleet availability check observed ruOS stopped/asleep. It was not started, accessed through exec, or kept awake. Storage, actual worker arguments, account credit and private receipt/case inventories were not inspected or freshened in this run. All prior financial observations remain historical. No model call, spending, ledger/cap mutation, training, image build, Arena POST or HF replacement occurred.

The existing output-contract comparison remains first in queue. The action-example candidate still requires independently audited private inventory and an immutable source seal, followed by fresh complete financial/source/input/worker admission and writable durable storage during permitted access.
