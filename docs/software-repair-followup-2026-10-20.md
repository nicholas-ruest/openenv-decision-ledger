# Software repair follow-up — 2026-10-20

The validated diagnostic runtime is `43b548debcb469af196a282bad07fc3bd8d33b15`, public amd64 image `ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:de25fc0311120f5eac114439fcf13be1b4d4f0bfc98289e29a03db1f013c396d`. [CI39511155304](https://github.com/nicholas-ruest/openenv-decision-ledger/actions/runs/39511155304) passed 459 tests, 143 anonymous native controls and six SDK checks. Earlier validated images remain available. Technical validation does not establish training or ranking improvement.

| Configuration | Unique prompts | Rollouts | Valid full repairs | Failures |
|---|---:|---:|---:|---|
| Release-d2, original allowance | 2 | 8 | 1 | 3 HTTP504, 2 budget, 1 truncation, 1 format |
| Release-d2, larger allowance | 2 | 8 | 5 | 2 HTTP504, 1 budget |
| Release-d3, broader verifier | 2 | 8 | 1 | 3 HTTP504, 4 format |
| Streaming transport probe | 1 | 2 | 0 | 1 pre-call ValueError, 1 format |

These are four different configurations, so their volumes are not a combined matched solve-rate estimate. All valid rewards were1. No screen passed the predeclared semantic-variation gate, no confirmation ran, and the default eight-task selection is unchanged. Failed-workspace terminal diagnostics remain posthoc; their labels and live scores were preserved.

The release-d3 verifier closes an independently demonstrated blind spot: a controlled implementation that ignores topological dependency readiness passes all six public and thirty hidden release-d2 cases, but fails ten of sixty broader contract cases. Release-d3 retains the contract, independent oracle, initial mutation procedure, reward and execution limits. Its public examples include a dependency-order witness, and its hidden suite mixes twelve witnesses with eighteen general release graphs. The older d2 task fingerprint is preserved. Thirty offline/native tests passed, including twenty-four constructed proper partial repairs; these are controls, not model rollouts. The new diagnostic remains outside the default mix.

The streaming probe returned four responses with stable identities and final token usage. One rollout then failed before another reservation. Its archived exception was only `ValueError`; immediate read-only checks at22:58UTC found zero exact `Qwen/Qwen3.8-27B` entries in the135-row HF router catalog. That is consistent with the pre-call model check failing, rather than proof that streaming fixes gateway errors. The other rollout copied the action schema. No model substitution or provenance relaxation occurred, and no causal transport benefit is claimed.

Follow-up runner changes persist completed samples while a slower sample is waiting, preserve ordered final summaries, record the failing operation and allowlisted error codes without exception text, and stop admissions when selected-model metadata is unavailable. They do not change tasks, rewards, action validation or the retained runtime image. Local regression tests verify archive persistence during a blocked sample and credential-safe failure reporting. Hosted checkpoint/thinking/Arena wrapper equivalence remains unattested.

A fresh local review bundle freezes128 workspaces across the unchanged eight provisional tasks, exact schema and an allowlisted source archive for the validated image. The [draft request](../config/software-repair-native-review-20261020.json) is unapproved and not ready to submit: the matching public HF bundle still needs publication and immutable verification. Historical HF previews remain separate. No Arena request was sent. This is preparation for review, not task-mix promotion.
