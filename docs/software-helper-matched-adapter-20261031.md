# Matched helper controller adapter: qualification only

The separate helper-preservation intervention now has matched qualification identities, a Native Trial adapter, explicit observation accounting and an independent trace replay. Both arms receive identical original prompts, source, public examples and action schema. Baseline keeps the original review protocol. Treatment restores only the two helpers explicitly declared complete in the public source, records controller authorship, and exposes a separate controller receipt. Public-pass automatic finalization is not part of this intervention.

A receipt serialization mismatch was fixed: controller messages now use the exact compact JSON counted by the observation budget. Native observations and controller receipts have separate token totals, and both consume the unchanged 8,192 completion allowance. First generation stays at 6,000, context at 24,576, and final-observation reserve at 96. Model usage includes all reported generation tokens, rather than only visible answer text.

Eight targeted tests passed using the pinned Native integration and cached public tokenizer. These include the original three prototype tests and five matched-adapter/replay tests. They check identical initial prompts; receipt cost and authorship; Native outcome and prompt tampering; truncation without controller recovery; rejection of incomplete, unknown-usage and extra-response traces; and refusal to relabel scripted artifacts as live evidence. A deliberately corrupted reference proposal is only a scripted control. Its repaired outcome is controller-assisted and is never a model solve.

All Native executions used the already-used qualification case. Planning metadata names separate future screen and confirmation identities, but `materialize()` unconditionally refuses production capture. There is no paid entry point or CLI/environment bypass. No new screen/confirmation case was materialized, no provider was called, and no spending or account-state mutation occurred.

Reproduce from the repository root with the pinned Python environment and public tokenizer:

```sh
HELPER_TEST_TOKENIZER=/absolute/path/to/tokenizer.json python -B -m unittest discover -s research/software-helper-controller-20261031 -p 'test_*policy.py' -v
HELPER_TEST_TOKENIZER=/absolute/path/to/tokenizer.json python -B -m unittest discover -s research/software-helper-controller-20261031 -p test_matched_protocol.py -v
```

`research/software-helper-controller-20261031/matched-qualification.json` binds the tested source and log hashes. The existing prototype qualification manifest was refreshed for the receipt serialization fix. Historical posthoc results remain bound to their actual earlier policy hashes; those are not new performance evidence for this adapter.

Live provider/failure handling, the finite caller, full assigned-phase assembly, controller-aware MetaHarness assessment, case inventory sealing and fresh private financial admission remain pending. Unknown usage is refused by this qualification-only trace reader; this is not a substitute for live reservation retention or failure closure. ruOS execution timed out and its heartbeat was stale during this preparation, so current private state was not reattested. No admission or improvement is claimed, and the continuation remains enabled.
