# Action-example assessment and Native replay qualification, October 31, 2026

The action-example candidate now has a method-specific assessment and an independent Native replay function, adapted from the existing output-contract evaluation code. The environment, Trial, SDK app, Native package, prompt intervention, assignment identities, sampler and budgets were not changed. The tested base is `9cffc0d8a199e08fbe6419426edfe2bab708da80`.

Ten assessment tests passed. They execute the pinned, unmodified MetaHarness fitness module at revision `b8c3d38de41203faf633ef6dceb8452a4727b0ea` on explicitly fictional qualification records. They preserve partial rewards, failure precedence, unknown usage, original assignment denominators and refusal of confirmation scoring. They also reject identical arm prompts, forged bindings, incomplete records and reused identities. This is actual execution of upstream fitness code for software assessment qualification, not actual model scoring or training.

Three Native replay tests passed in 7.728 seconds. Scripted trusted-reference responses are reconstructed through fresh actual Native Trials with the existing pinned accounting helper. No provider is called. Replay verifies the exact original chunk, assigned events, sent request/message hashes, response identities, usage, final Native category and grade, observations, and unchanged 8,192 generation-plus-observation / 24,576 context limits. Tampered usage, request, identity, grade, extra choice, unassigned event and altered protocol inputs are rejected. The first proposal limit remains 6,000.

The public tokenizer was downloaded from the declared model revision and independently matched the existing SHA256 pin `0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3`. The installed tokenizers version is the repository's calibration lock value, `0.23.3`. These are documented local counts, not attested production Arena actor serialization or thinking behavior.

The first replay attempt stopped before any trace execution because the qualification harness lacked the integration import path. The harness now loads the unchanged accounting integration through its normal path; the successful rerun is separate and the failed log remains preserved. No fallback accounting or manufactured usage was used.

Reproduce with the existing locked test environment plus the calibration lock:

```bash
cd research/software-action-example-20261030
node --test test_assess.mjs
ACTION_EXAMPLE_TEST_TOKENIZER=/absolute/path/to/pinned-public-tokenizer.json PYTHONDONTWRITEBYTECODE=1 python -m unittest -v test_replay
```

The replay tests explicitly skip if no tokenizer path is provided; a skip is not qualification. This run supplied the verified tokenizer and passed all three tests without skips. Assessment log SHA256: `081d1c5507ca9fd49af9a96fed3ceacfdd99113b9693fbfb06ea986063ab2025`. Successful replay log SHA256: `9ae9efcaeaf596bb227c5d2bae8fd54cdbb57f0cfeba21b3568ff129f770b5c2`. [Machine-readable qualification receipt](../research/software-action-example-20261030/assessment-qualification-20261031.json).

The verifier accepts supplied traces; it does not establish their provider authenticity or authorize execution. No live caller, full live-phase assembler, source/admission binding, or paid entry point was added. Independent case-overlap auditing against all earlier private materialized cases, a finite admitted caller, fresh complete account/receipt reconciliation and writable durable ruOS storage remain required. Confirmation stays unmaterialized. The already-qualified output-contract comparison remains first in queue.

No ruOS access, credentials, financial mutation, model calls, training, image build, Arena POST or HF replacement occurred. Frozen v12 is unchanged. The known broader process-coordinator regression remains unresolved. These controls do not establish a candidate performance gain or leaderboard improvement.
