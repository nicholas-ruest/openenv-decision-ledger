# Action-example Native Trial and source SDK qualification, October 31, 2026

The separate action-instance prompt prototype now passes actual Native Trial and OpenEnv source-app checks in an isolated Codex worktree. ruOS was not accessed after its fixed stop. No model calls, spending, training, image build, dataset replacement or Arena submission occurred.

The tested base is `484fa11b6192f6ecea831041342f85d494e7e919`, with the added source app and two new test files. The existing environment and protocol logic were unchanged. All 17 Native package files are byte-identical to `bc9a7fab8392c17a6f1d4bf27a6aa50c92df9ebb`.

| Checks | Passed | What they establish |
| --- | ---: | --- |
| Existing actual Native environment checks | 7 | Note-only initial prompt change, baseline parity, unchanged Native grades and schema-echo behavior |
| New actual Native Trial checks | 5 | Original-problem identity, identical system schema, required public review at reward zero, trusted reference retention/repair, schema-echo termination and invalid-action refusal without retry |
| New actual OpenEnv HTTP/WebSocket checks | 3 | Unchanged typed schema, treatment note in the real reset, public review/final grade, and isolation of concurrent sessions |
| Existing offline protocol checks | 5 | Assignment/sampler/budget binding and sealed confirmation refusal; these are not Native trajectories |

The two arms receive the same original task, source, examples, schema and public review. Only the fixed action-instance note differs at reset. Trusted reference modules reach the same final full grade. A schema echo still follows the original empty-content terminal behavior; malformed JSON remains a format failure with no Native step. No rejected output is repaired, retried or excluded.

The actual OpenEnv revision is `86a180ede21e044f7929b9a7783ad83aa67d83a3` (installed SDK `0.6.1.dev0`). Dependencies were installed from the repository's exact runtime lock in an isolated Python 3.12 environment. The lock SHA256 is `3fbed6fc6af3931cdacd290353a02ba1740222974c91a022145ec4e6a5f3a347`; pip check reported no broken requirements.

Reproduce from this source with that locked environment:

```bash
cd research/software-action-example-20261030
PYTHONDONTWRITEBYTECODE=1 python -m unittest -v test_action_example_environment test_action_example_protocol test_action_example_trial
PYTHONDONTWRITEBYTECODE=1 python -m unittest -v test_action_example_app
```

The first command passed 17 tests in 4.813 seconds, log SHA256 `168deec3293ba30e68d6644f16d848b9f64354dbd8e035c00ff0ebc3d7002381`. The second passed 3 tests in 1.123 seconds, log SHA256 `9c1d5137ada887a54fde08d76b0b04d6140c5c709fb148885bb917e18e02c137`. The [machine-readable receipt](../research/software-action-example-20261030/native-trial-qualification-20261031.json) preserves the remaining admission limits.

Native qualification materialized the proposed screen case, using trusted reference controls without exposing their source in the public receipt. Confirmation remains unmaterialized and refused by this screen protocol. No screen inputs were frozen and disjointness has not been independently audited against all prior private archives. New seed numbers alone are not evidence of disjointness.

This is source-app qualification, not a Docker-image or production Arena actor-equivalence attestation. Independent live-trace replay, assessment/caller binding and current financial admission remain pending. The previously documented broader process-coordinator regression remains unresolved. The existing output-contract comparison stays first in queue, and the frozen v12 request remains unchanged.

These passing controls are not model solves. No inference-policy improvement, software transfer or leaderboard gain is established for action-example prompting.
