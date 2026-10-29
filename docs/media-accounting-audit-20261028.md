# Saved generation and observation accounting verification — 2026-10-28

The preceding parent verifier checked record hashes and final assessments but trusted the worker's saved accounting totals. A separate phase variant now writes the exact local accounting configuration before opening a native environment, and binds its hash into the claim, resets and pre-dispatch intents. The earlier phase implementation and both reviewed requests remain unchanged.

The configuration freezes completion/context limits, serialization, tokenizer bytes and package version, special-token/padding/truncation flags, counter implementation and relevant source-file hashes. A factory with different limits or implementation fails before reservation/dispatch. Synthetic counters are explicitly marked.

`accounting_archive.verify_archive` takes an external trusted configuration, counter, ledger and replay adapter. It reconstructs histories from saved raw provider/native events; independently adds generation and full post-reset observation costs; checks each reservation against the reconstructed allowance; re-runs the semantic auditor; reconstructs the overflow classification and final 16-attempt assessment. It does not call the runtime budget's accounting/projection methods. Raw native rewards remain preserved. Saved provider records, event records, resets and intents must agree with the episode archive.

Fifteen offline tests pass locally: valid multi-action and failed-provider phases; initial and post-action overflows; changes to saved costs/configuration/source manifest/intent/provider records/classification; mismatched budget factories; failed configuration persistence; duplicate JSON keys and symlinks. All callbacks and counter values in these tests are synthetic. CI [40694731465](https://github.com/nicholas-ruest/openenv-decision-ledger/actions/runs/40694731465) passed the same 15 tests on Python 3.12. The detached source checkout on ruOS passed 15 tests too. A separate 16-attempt scripted phase used the existing hash-pinned tokenizer with tokenizers 0.23.3: all saved costs were independently recomputed and an altered-cost archive copy was rejected. Provider and native callbacks remained synthetic; this adds no model-performance evidence. All remote commands completed with verified exit code 0.

The verifier shares the pinned counter, canonical serializer and semantic auditor; it is independent arithmetic and history reconstruction, not an independent tokenizer implementation or cryptographic proof of provider execution. Source/configuration hashes bind the supplied local method, not dispatch chronology or account truth. The replay callback is caller-supplied and must itself be bounded/trusted. Only complete archives are accepted; this is not a resume mechanism. The parent supervisor has not yet been wired to require this verifier for accounted phases.

Arena chat-template/special-token/hidden-reasoning and observation-wrapper equivalence remain unverified. This is a local proxy accounting method, not a production equivalence claim. No model calls, new training, improvement estimate, submission or HF replacement occurred. Software v12 and media v13 stay frozen and unapproved.

## Reproduce the cached-tokenizer control

With the six research directories used in the CI command on `PYTHONPATH`, run this from the frozen source checkout using an existing matching tokenizer; no tokenizer/model download or provider call is made:

```python
from pathlib import Path
from test_accounting_archive import ArchiveTests
from observation_budget import PinnedCounter

case = ArchiveTests()
case.setUp()
try:
    case.counter = PinnedCounter("/absolute/path/to/existing/tokenizer.json")
    case.run_phase()
    result = case.verify()
    assert result["episodes_recomputed"] == 16
    assert not case.config["synthetic_counter"]
finally:
    case.doCleanups()
```

Next: require the new verifier in the parent supervisor for accounted phases, then test its bounded composition against the unchanged native image. No paid phase is admitted by this work.
