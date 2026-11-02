# Saved first-proposal runtime diagnosis

Two distinct first proposals from the closed entry-order screen rewrote the same supplied working helper and passed a list to an integer-bound loop. The helper AST was identical in both proposals. Each first proposal passed 2 of 6 supplied examples and raised TypeError on the remaining 4.

Restoring only that original helper made each proposal pass all 6 examples. The entrypoint and every other module statement remained AST-identical. Both saved final revisions already passed all 6 supplied examples and had earned full Native grade in the original closed screen. Neither of these two attempts received computed-relation feedback. This diagnosis explains first-turn failures; it supplies no additional model solves or causal evidence for feedback.

| Saved arm | Original first | Helper-restoration control | Saved final |
| --- | --- | --- | --- |
| relation_only | 2/6; 4 runtime errors | 6/6; 0 runtime errors | 6/6; 0 runtime errors |
| computed_relation | 2/6; 4 runtime errors | 6/6; 0 runtime errors | 6/6; 0 runtime errors |

These are two proposals on one underlying case, with a posthoc investigator edit. No new case, model call, hidden-case replay, training, or fresh confirmation occurred. The original failed selection and closed preservation studies remain closed. The separate prepared final-output-domain reminder remains unchanged and unadmitted. Do not select another preservation intervention from these already self-corrected first-turn errors.

## Reproduction

Analyzer source: [b973e7b](https://github.com/nicholas-ruest/openenv-decision-ledger/commit/b973e7b75ca794ffc1ae0645cf5d900dfa1348ac). Run `research/software-helper-runtime-audit-20261102/analyze.py --archive PRIVATE_CLOSED_ARCHIVE --helper-name PUBLIC_SUPPLIED_HELPER --output FRESH_PRIVATE_OUTPUT` with the original Native dependencies. Private trajectories and case inputs are required and are not published.

The analyzer checks the recorded clean source and Native hashes, then evaluates submitted code exclusively through the original Native Program interpreter. It extracts the trusted, pinned framework equality function for comparison. It restores exactly one supplied helper, verifies all other module statements are unchanged, and verifies the request/reply files remain unchanged. The reproduced aggregate JSON was obtained on ruOS with exit 0 and empty stderr. No interpreter limits, task difficulty, original worker outputs, accounting files, or selection rules changed. No MetaHarness execution is claimed for this diagnostic replay.

Native SHA-256 pins are included in the aggregate JSON. Private supervision and attribution journals are retained separately; public results contain no raw inputs or model code.
