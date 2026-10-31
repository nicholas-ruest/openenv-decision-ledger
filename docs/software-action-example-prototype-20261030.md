# Action-instance example: separate unmeasured software prototype

Saved model responses in the prior function-review screen and confirmation included JSON Schema echoes. The unchanged action type ignores undeclared fields and defaults content to empty, so a schema echo terminates as an empty action. The model study counts these outcomes as observed; they are not silently repaired or excluded. This motivates a separate prompt intervention, not a claim that serialization advice will improve solves.

The treatment appends this fixed, task-independent action-shape example to the initial reset prompt:

> Action serialization example: {"content":"<complete repaired Python module>"}. Replace the placeholder with your actual Python source, encoded as a JSON string. Return an action object with field values; do not return the JSON Schema description of the action. The example is only an output-shape guide, not a solution.

Both arms inherit the actual Native joint `software_repair-ignore-d2` baseline from source `67d23ab24220fab022f2eb58bffc81d951b092c5`, using standard-contract reset behavior. Neither arm includes the separate output-key reminder. Schema, parser, examples, source, Native grading, public field/runtime feedback and required review behavior are unchanged. First nonempty proposals still receive reward zero; empty content still ends the episode. Unknown submit fields cannot bypass review.

Seven focused actual Native tests passed in 3.301 seconds. They check exact baseline reset parity across three seeds, note-only treatment differences, public-only review parity, unchanged correct/wrong final grades, unchanged schema-echo termination, no early hidden submission, and task/arm rejection. The 17 Native Python files match the pinned baseline byte for byte. The full test-log SHA256 is `f1a0f32182b7a5e32e4471eb5d7150810470f6b02426b67322ac8af546113241`; source hashes and limits are in the [qualification receipt](../research/software-action-example-20261030/qualification.json).

Reproduce from this repository with the existing OpenEnv environment:

```bash
cd research/software-action-example-20261030
PYTHONDONTWRITEBYTECODE=1 python -m unittest -v test_action_example_environment
```

The tests ran in an isolated source archive of the pinned baseline plus these two new files. They used the existing ruOS Python environment, no model/provider credential, and temporary qualification storage. Existing data, caches, ledgers and response archives were preserved.

**No model calls or performance results exist for this intervention.** It has no bound paid caller, frozen paired protocol, materialized screen or confirmation, built image, or Arena actor-equivalence attestation. The broader existing process-coordinator regression remains unresolved. This does not change or replace the frozen v12 request, HF dataset, output-contract study, or any accounting guard.

The already-qualified output-contract screen remains first in queue. Its durable reservation/response admission is blocked by the full ruOS data volume. After storage is restored, any later action-example comparison needs its own frozen baseline and treatment prompts, matched sampling and unchanged 8,192 generation-plus-observation / 24,576 context budgets; complete verified assignments; a prespecified screen gate; and fresh disjoint confirmation without redesign. Native controls are not model training or measured improvement.
