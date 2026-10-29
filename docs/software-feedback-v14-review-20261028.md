# Separate software feedback v14 review candidate

The exact request and matching dataset manifest are frozen at
[`cc48e2b1f47603c569fffac2eacfa28d35539ed4`](https://github.com/nicholas-ruest/openenv-decision-ledger/tree/cc48e2b1f47603c569fffac2eacfa28d35539ed4).
They are **unapproved and unsubmitted**. No HF dataset was replaced.

- [Exact request](../config/software-feedback-v14-review-20261028.json), byte SHA-256 `2cf57b603a61d1d9cbca39995123c13a62e5306fcdadbee3395eabbfac8b0ae7`.
- [Staging manifest](../config/software-feedback-v14-staging-20261028.json).
- [Reproducible generator and tests](../research/software-revision-review-20261028/).
- Qualified runtime source `ae301b0a4071b5a376d6eeef6812060fac789534`; image `ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:a842e4ec292f9aa5067514a7eb8a85b5fa1e43edda61ef2bb53b9704603f8144`.
- Prior image qualification [CI 40742200919](https://github.com/nicholas-ruest/openenv-decision-ledger/actions/runs/40742200919): anonymous pull, six SDK checks, exact schema and four scripted WebSocket episodes. Those checks concern the image, not this newly staged bundle.

Two bounded bundle tests passed on ruOS using its existing Python environment,
from a fresh detached worktree at `6ef4c9e59ee45567a6a4a8c6baa90e9eb76cf3d4`.
They recaptured all 48 native reset observations, checked identities and split
seeds, and independently rebuilt identical request/source/dataset hashes.
The source allowlist was byte-compared with the qualified image source commit.
The full native schema hash matches image qualification; only its action and
observation schemas are copied into the request, as required by the Arena guide.
Both task admission sequences and early finish terminate at zero reward.
No new CI workflow was installed; automated review rejected that proposed workflow
under the no-new-automation instruction. Bundle tests were executed on ruOS.

The staged dataset has 32 train, 8 validation and 8 test **public reset examples**,
not model trajectories or hidden answer sets. The runtime generates fresh episodes
and does not read this dataset. The currently published HF dataset still documents
v11. This request must not be submitted against that stale dataset: matching
replacement is separately approval-gated. Existing v12, v13 and v11 rollback remain
unchanged. Exported public test seeds cannot serve as unseen model confirmation.

This candidate tests computed public-example feedback after a first repair proposal.
It allows two responses and retains v12's 8192 completion / 24576 context token limits;
the tool-call count changes from one to two. Its two prerequisite tasks omit v12's
joint d2 task. These changes prevent attributing a future effect to feedback alone
without the separate matched neutral-review comparison. That research protocol uses
4096/8192 token limits, so it does not establish equivalence with this request.
Working-helper preservation remains a separate intervention and is not added here.

No model calls, model revisions, training or Arena submission ran in this step.
The existing allocation has not admitted the complete matched comparison. Reference
and negative controls are not training or model improvement. Fresh disjoint model
confirmation remains absent; private transfer and leaderboard gain remain unmeasured.
This is candidate preparation, not a promotion or a recommendation based on proven
model benefit. There were no Slack, Arena board or PR conversation updates.
