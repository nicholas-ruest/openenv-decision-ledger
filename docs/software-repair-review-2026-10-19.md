# Software repair candidate review, October 19

The compact-fixture runtime is image-validated. The review bundle contains 128
visible workspaces for the unchanged eight provisional software tasks. This is
an unapproved draft; it has not been submitted to Arena.

- Runtime: `7156868d300b29037440f69361ceca5b02da5724`.
- Public amd64 image: `ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:8e0e98807f74fb6c587f8e36aba14fdc6ee8f917693cf7b6bd6e0f7e6c77e263`.
- [Native validation](https://github.com/nicholas-ruest/openenv-decision-ledger/actions/runs/39304763223): 247 CI tests, 115 anonymous native controls, six SDK checks.
- [Exact draft request](../config/software-repair-review-20261019.json).
- [Bundle manifest and source-file hashes](results/software-repair-review-manifest-2026-10-19.json).
- [Validation and separate saved-workspace diagnostic](results/software-repair-fixture-validation-2026-10-19.json).

The historical `config/software-repair-submission-candidate.json` and Hugging Face
software preview remain older artifacts. The public Hugging Face dataset is
still at `063900b75ac26423166a80d11e814092b1d05627`; the current bundle has not
been published there. Dataset refresh and immutable public verification remain
required before submission review can be completed.

## What the evidence establishes

Complete public examples retain all their typed inputs and expected answers,
using 12–21% fewer observation tokens across 18 matched offline instances.
Model-success benefit is unmeasured. The preceding focused-example screen had
three full repairs over eight attempts on two prompts, with three episode-budget
failures and two provider timeouts. Valid completed rewards were all 1, so there
was no confirmation. Release/plan diagnostics remain excluded from the default
training mix. Native reference controls are not model solves or training results.

Exact saved-action replay separately found one budget-failed workspace with
offline finish reward 0.25. That diagnostic preserves the failed live episode;
it does not add a partial solve, establish a training signal, or justify promotion.

## Required review before any submission

1. Publish the current `software-repair/` bundle and verify every uploaded file
   against the manifest at its immutable dataset revision.
2. Recheck the request's image, runtime, schema, task list and dataset revision.
3. Show Nick the exact request and obtain explicit interactive approval.

No confirmed trained-model improvement, ranking improvement, signed promotion,
merge, or new Arena submission is claimed. Hosted checkpoint/thinking and Arena
wrapper equivalence remain unattested. The prior validated images remain rollback
options. No submission operation exists in the offline bundle builder.
