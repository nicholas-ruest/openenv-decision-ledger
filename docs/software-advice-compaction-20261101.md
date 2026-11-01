# Compact fixed failure advice before a sealed screen

The proposed failure-only advice now uses a shorter fixed note. The existing public-review message already asks for a complete final module and one revision. The added note focuses on the exposed contract violation, reusing unaffected code, completing the JSON action and preserving requirements beyond the supplied examples. This preparation changes no submitted candidate code, action schema, sampler, grader or budget.

On the already-used qualification case, with tokenizer SHA `0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3`, the complete canonical environment advice receipt changed from **103 to 69 tokens**, saving **34 tokens (33.0%)** whenever delivered. This counts the receipt envelope as well as the note. First prompts, Native public-review observations, transcript before the appended receipt and all other receipt fields were identical. The full Native-plus-advice observation cost was independently checked for both notes.

This is a fixed-text token-cost control, not evidence that the compact wording improves model behavior. No model calls or new procedural cases were used. The prior note is AST-read from public commit `3ecd31f88fdfb055dcbf041c515da8702eef5adb`; it is not executed. The sanitized result is [software-advice-compaction-20261101.json](software-advice-compaction-20261101.json).

All **32 advice-suite tests passed**, including actual tokenizer receipt accounting, unchanged Native feedback, independent request/trace replay, exposure-aware execution of the pinned MetaHarness fitness module, incomplete/unknown-usage handling, deadline and financial-delegation controls, and refusal of an unsealed live launch. Live-path test inputs are mocked controls on the already-used qualification case; these are not model evaluations.

Reproduce from the repository, with the pinned tokenizer available locally:

```sh
python -B research/software-failure-advice-20261031/compare_advice_tokens.py \
  --tokenizer /path/to/tokenizer.json --output /fresh/path/cost-control.json
HELPER_TEST_TOKENIZER=/path/to/tokenizer.json python -B -m unittest discover \
  -s research/software-failure-advice-20261031 -v
```

The live materializer remains sealed by default. A future private case audit and execution-source lease must bind this compact method, followed by the existing independent replay, current credit and complete reservation/parent reconciliation, whole-phase admission and worker/operating-window guards. No closed screen is reopened. This offline preparation uses no ruOS access after the fixed cutoff and does not freshen billing, change the allocation or authorize execution. Frozen v12 remains untouched and unapproved.
