# Software task learning diagnosis — October 27, 2026

Public Trackio run `a3274296c46341a847407f97` contains 148 optimizer-step records. The new analyzer joins by exact step and rejects duplicate, non-finite or invalid step records. Missing metrics remain unavailable; retried steps are separate. It reads no credentials and issues no inference or submission requests.

| Recorded task ID | Clean steps | Nonzero std + gradient | Zero-variance | Saturated | First/last 10 clean reward |
|---|---:|---:|---:|---:|---|
| 1 | 50 | 38 | 12 | 0 | 0.189 / 0.154 |
| 2 | 48 | 38 | 10 | 10 | 0.651 / 0.864 |
| 3 | 48 | 45 | 3 | 0 | 0.421 / 0.407 |

IDs 2 and 3 each have one additional retried step. All seven metric series joined without missing/unassigned steps. Numeric IDs are recorded by Trackio, but the task-name mapping is not attested. Do not assign family names from rotation or change family weights on this evidence alone. Nonzero reward std and gradient indicate optimizer signal, not semantic correctness, independent samples, held-out improvement or productive reasoning-only groups. Early/late windows also cover changing generated prompts.

The immediate hypothesis is unequal learnability/saturation across the mix; it is not confirmed causal evidence. Resolve the task mapping from an actual trainer log/config before selecting a family adjustment. Preserve the qualified runtime and the v11 request.

## Executed checks

- Seven exact-step analyzer regression tests passed, covering reordered/gapped steps, retry exclusion, unavailable metrics, duplicate identity and malformed values.
- Real upstream MetaHarness source `b8c3d38de41203faf633ef6dceb8452a4727b0ea`: 25 fitness and signed-gate tests passed using `node --experimental-strip-types --test integrations/openenv-arena-darwin/test/fitness.test.mjs integrations/openenv-arena-darwin/test/gate.test.mjs`. These are offline regression tests; no search, model training or promotion was executed.
- Focused calibration protocol is prepared only. It requires frozen matched settings, repeated identical prompts, disjoint confirmation and existing budget reconciliation. No new calls, purchases, image changes, dataset replacement or Arena submission.

Reproduce: `python3 scripts/analyze-task-learning.py --project GlobalBusinessAdvisors --run a3274296c46341a847407f97 --output /tmp/fresh-task-analysis.json`. Raw public metric records remain available from Trackio; the summary includes their canonical SHA256.

Dashboard: https://openenvarena-training.hf.space/?project=GlobalBusinessAdvisors&runs=a3274296c46341a847407f97
