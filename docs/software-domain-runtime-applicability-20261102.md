# Final-domain reminder: runtime applicability and separate candidate

The frozen v12 source app is one-response. Its `direct_app.py` selects `DirectRepairEnvironment`, whose first submission terminates the episode without a review turn. The separately reviewed v14 image has a different two-response interface: `content` plus `submit`, optional early submission, and public-example feedback. The qualified final-domain comparison instead uses content-only actions, a mandatory review turn and a late reminder. Neither reviewed image is an equivalent serving implementation of that comparison.

Three source-runtime probes used the **already-seen ignore-d3 seed 2560000** and a synthetic compile-rejected module, with empty retention where needed. No model responses, hidden evaluation tasks or new cases were used. These were source executions in the installed Native/OpenEnv environment, not container-image executions.

| Source runtime | Action properties besides metadata | Observed first result |
|---|---|---|
| v12 pin `0b8ccc3ca70a67fed5fc5837b69022261cc60497` | content | terminal, no review |
| v14 pin `ae301b0a4071b5a376d6eeef6812060fac789534` | content, submit | requested early submission terminates |
| Qualified reminder source `8a42c73babefb87e421b4f4987494d2daeaef69a` | content | nonterminal review with reminder; second response terminates |

The current comparison's interpreter also differs from the v12/v14 source pins. `runner.py` and its documented subset in `tasks.py` changed; `direct_app.py`, `direct_environment.py`, `environment.py` and `ignore_repair.py` match across these probes. The retained JSON records contain actual file hashes. This is another reason not to infer image equivalence from an old image's dependency availability. It is not a model improvement finding.

## Separate runtime candidate

`research/software-domain-runtime-20261102` prepares a distinct app and Dockerfile. The environment reuses the qualified two-response wrapper, retains identical first prompts for control/treatment, and adds only the late reminder in treatment review. It serves the existing ignore-d3 task with native runtime seeds. Controls here use only the already-seen fixture. No reviewed app, request, dataset, image or qualified comparison method is retargeted.

A declared trainer finish action uses the existing action `metadata` field with `decision_ledger_finalize: true` and empty content. It grades immediately from reset, or retains and grades the actual first proposal. It does not add a `submit` schema property. Invalid finish metadata refuses before state changes. Normal two-response model actions follow the existing wrapper. This finalization integration is new runtime behavior and needs explicit request/image qualification; the comparison's previous scripted qualification does not establish equivalence for this finish path.

The Dockerfile starts from the unchanged pinned v12 dependency image, copies the current interpreter/task package explicitly, and includes only the required wrapper/review/runtime modules. It contains no provider, credentials, billing logic or submission driver. Its default is the separate treatment app; its control arm is available for source tests. It is an unapproved candidate and has no published replacement image or new Arena request.

Five local tests passed: shared initial prompt/isolated reminder, Native final grades before/after proposal, terminal idempotence, invalid finish metadata without state mutation, task-scope refusal before generation, and actual OpenEnv SDK WebSocket metadata finalization (some assertions share a test). Reference reward is an oracle control, not a model solve. Container packaging, anonymous SDK/runtime checks and model confirmation must be reported separately. Existing accounting/admission and exact-request interactive approval requirements still apply; no spending cap, resources or comparison scope is changed to fit the remaining allocation.
