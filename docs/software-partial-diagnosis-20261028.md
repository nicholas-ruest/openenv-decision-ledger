# Saved software repair localization

This offline diagnostic replays an existing fixed16-response archive through its source-pinned runtime before analyzing failures. It compares top-level supplied function ASTs, ignoring formatting, and measures single-function and combined restoration of altered public supplied functions. These are posthoc interventions over existing responses, not model calls, held-out confirmation, training or improvement. Counterfactual results cannot be reported as model solves.

Candidate code is parsed for structure and evaluated only by the existing bounded Python-subset interpreter. It is never passed to host exec/eval. Missing functions and duplicate identities are not silently repaired. Each intervention is measured against the same hidden/public cases as its unchanged candidate. The report retains failed inputs privately for diagnosis; raw responses, private grading and input records must not be published.

Four unit tests pass locally. The diagnostic leaves reviewed softwarev12/media-v13 requests, runtimes and datasets untouched. No public channel or PR conversation post accompanies this work.

CI40712511117 passed all4 tests. The source-pinned existing16-response archive was replayed successfully in an isolated ruOS checkout; private per-response diagnoses and counterfactual scores remain on ruOS. No new model calls or training occurred.

A future comparison should use the already prepared baseline/preserve-supplied matched protocol, frozen identical reset/workspace hashes within each pair, a fixed whole-phase allocation and independent fresh confirmation. Public-example self-checking is a separate intervention and must not be bundled into that comparison. Altering or repairing saved responses after observing failures is diagnostic only; it cannot be counted as fresh confirmation or used to claim target-model learning.
