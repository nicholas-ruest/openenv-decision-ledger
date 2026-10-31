# Guarded helper transport and process supervision

The helper controller now has a source-guarded bridge to the existing financial/provider backend and the existing Linux process supervisor. It delegates the original receipt, reconciliation, tokenizer and explicit amendment digest to the existing `LiveBackend`; it does not create a new cap, ledger, route, credential source or reservation implementation.

Live admission is checked before backend import, credential lookup, route quotation, private artifact inspection or process creation. Exact clean-source checks and hashes bind the reused backend, amendment-aware reservation gate, streaming transport, whole-phase quote module and supervisor. Production materialization remains independently blocked. This revision does not implement or admit the final helper-specific live case mapping and evidence path.

Six focused tests passed. They verify guard ordering, unchanged backend-argument delegation through a mocked constructor, the fixed 23:00 Toronto stop and 1,200-second supervisor ceiling, successful completion/replay of an existing qualification chunk in an actual supervised local worker, timeout shutdown of that worker, and rejection of changed dependencies, reused archives and non-scripted qualification backends. The timeout proof is local worker shutdown, not remote provider cancellation or a billing refund.

All actual worker executions used scripted qualification responses on the already-used case. The delegation test made no provider request and loaded no credential. No new screen/confirmation case, model call, financial reservation, purchase, dataset replacement or Arena request occurred. Controls are not training, performance or leaderboard evidence.

Reproduce with the pinned Python environment and cached public tokenizer:

```sh
HELPER_TEST_TOKENIZER=/absolute/path/to/tokenizer.json python -B -m unittest discover -s research/software-helper-controller-20261031 -p test_transport_bridge.py -v
```

`transport-qualification.json` binds the tested bridge, tests, dependency pins and log hash. Earlier qualification manifests remain historical snapshots of their recorded revisions, not cumulative performance evidence. The current Arena guide was fetched and matched the previously read guide hash; board retrieval returned an HTTP error. No public conversation posts were made. Frozen v12 and the closed finalization study are unchanged.

ruOS read access recovered during preparation and showed the last-known ledger hash unchanged with no caller/Darwin worker running. This alone is not fresh financial admission. Current credit and the complete parent/root reservation audit still require reconciliation. Paid helper execution remains blocked until the helper-specific live materializer, audited evidence path, immutable case lease and fresh accounting/credit admission are complete.
