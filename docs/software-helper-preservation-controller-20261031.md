# Public-source helper preservation controller prototype

The public ignore-repair contract explicitly declares `match_segment` and `match_parts` complete reusable helpers. Earlier private replay found a response that broke a supplied helper. The separate prompt-advice intervention did not establish a gain; this prototype instead restores only these two supplied function definitions when a parsed, stop-terminated model action changes or omits them.

The transform reads only the initial public source and the explicit public declaration. It does not access reference solutions, hidden tests, Native grades, billing, credentials or a provider. Repair targets remain the model's proposal. Malformed proposals, duplicate helper definitions and absent declarations remain unchanged. Restoration may interfere with a valid alternative implementation that deliberately changes helper semantics; a matched model comparison must measure that risk.

Controller edits are not attributed to the model. The Trial transcript retains the actual model reply; a separate controller receipt describes each transformation. Every Native observation and controller receipt must consume the original completion budget. Empty model actions retain their original meaning. This prototype does not automatically finalize public-passing proposals and does not combine the two interventions.

Three targeted tests passed with the pinned Native integration on the already-used `software_repair-ignore-d2` qualification case. They cover restoration of a deliberately corrupted helper, retention of unrepaired target logic, unchanged malformed/ambiguous inputs, actual-model transcript provenance, and both Native/controller observation accounting. The deliberately corrupted proposal starts from a reference solution solely as a scripted control. It is not a model response or measured solve.

Reproduce from the repository root with the pinned Python environment:

```sh
python -B -m unittest discover -s research/software-helper-controller-20261031 -p test_helper_policy.py -v
```

`research/software-helper-controller-20261031/qualification.json` records the tested source hashes and environment versions. No future screen or confirmation case was materialized by these tests, and no model calls occurred. A controller-aware matched protocol, finite caller, independent replay and admission are still required. This is a source prototype, not a training environment, Arena deployment or performance improvement.
