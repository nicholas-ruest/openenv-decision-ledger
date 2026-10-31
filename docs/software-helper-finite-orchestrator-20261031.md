# Finite helper controller orchestration: qualification only

The separate helper-preservation candidate now has finite orchestration for two original assignments per chunk, four chunks per planned phase, and at most two responses per attempt. It reserves before every backend call, writes durable call/response/failure records, counts Native observations and controller receipts separately, and retains unknown usage without a refund API. A failure stops later assignments; an earlier known reply never makes a later unknown-usage call appear known.

Six focused tests passed with the pinned Native integration and cached public tokenizer. One test runs all four scripted qualification chunks and independently replays all eight assigned outcomes. The others verify reservation denial before a provider call, unknown usage after an earlier known reply, Native initialization failure, fresh-archive enforcement, both source-bound live-execution blocks, and deadline expiry after reservation or Native processing. The full qualification fixture makes sixteen scripted backend calls, not provider calls. Reference-derived control responses and controller-assisted outcomes are never reported as model solves.

The original limits remain: first generation 6,000; generation plus Native/controller observations 8,192; context 24,576; final observation reserve 96; request timeout at most 360 seconds; attempt deadline at most 600 seconds; two model responses; no retries. The caller requires an outer phase deadline, checks time again after a returned reply, and stops if the response or observations exceed budget. This in-process qualification runner does not claim process-supervisor or production-wrapper equivalence.

`finite_caller.py` accepts only explicitly scripted qualification backends. It contains no credential loading, live provider transport, purchase, account or real-reservation mutation implementation. `--execute` refuses at the unsealed source/case guard before backend construction. Production materialization remains independently blocked in `matched_protocol.py`; a CLI argument or environment variable cannot admit a future case.

Reproduce in the pinned Python environment:

```sh
HELPER_TEST_TOKENIZER=/absolute/path/to/tokenizer.json python -B -m unittest discover -s research/software-helper-controller-20261031 -p test_finite_caller.py -v
```

`finite-caller-qualification.json` records source and test-log hashes. All Native controls use the already-used qualification case. No new screen/confirmation case, provider call or allocation mutation occurred. The receipt serialization fix and prior matched-adapter qualification remain unchanged.

Production provider/failure integration, supervisor wiring, complete-phase assembly and controller-aware MetaHarness assessment remain to be implemented and tested. Case inventory sealing and fresh private financial admission are also pending. ruOS execution timed out again, so current reservations, private state and credit were not reattested. Guide retrieval returned an unsupported Markdown content-type and the board was unavailable through the read tool; no public conversation posts were made. Frozen v12 is unchanged. This source is preparation, not training or measured improvement.
