# Public-example overfit negative control — October 29, 2026

Executed a deliberately wrong, public-only lookup implementation through the separate two-response revision environment. The constructor received only the six supplied examples; it had no task object, hidden cases, reference implementation, model response, or repair oracle. Unrecognized inputs returned all entries included. Candidate code ran solely in the unchanged bounded interpreter.

In both ignore-d3 and ignore-d4 at research seed 2470000, this implementation passed all six public examples without execution errors, received zero intermediate reward, then earned **zero native terminal reward**. The final empty submit retained exactly that module. The module was 1,978 bytes, under the unchanged 8,192-byte limit. Both tasks shared the same visible examples and lookup source; this is one constructed counterexample across two task variants, not two independent problem cases or an estimated failure rate.

This validates a limitation of the public self-check intervention: all-pass feedback does not establish full-contract correctness. Preserve native semantic reward as the outcome; do not promote, stop revising, or reweight training merely because public examples pass. The existing environment already awarded no intermediate reward and retained full-contract terminal grading; no reviewed runtime/request or protocol was changed.

Reproduce from the tested source `2f46837febfb99177a5b5c46c1477ab1a7e3ed2b`, using its native OpenEnv dependencies:

```sh
python research/software-public-overfit-20261029/probe.py --output /fresh/path/result.json
```

This was an authored negative control, not sampled model behavior, MetaHarness search, training, fresh model confirmation, or evidence of ranking improvement. There were no provider calls or financial reservations. It establishes possibility, not prevalence or the intervention's effect on a model. Fresh disjoint model evaluation remains necessary and financially unadmitted under the existing guards.
