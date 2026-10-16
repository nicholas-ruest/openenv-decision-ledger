# Darwin decision — October 12, 2026

Decision: retain the unchanged baseline. No evolved candidate is promoted.

The thinking-enabled, untrained hosted-model baseline solved **54 of 64 unique cases** (84.375%). Three valid child measurements tied the baseline's training-signal fitness (3.0714285714); one scored lower (2.2857142857). Five other child variants were refused with `max_new_cells_exceeded: 8 > 1`. Refusal is not a performance measurement. The search therefore has limited coverage.

No measured child beat the baseline. Fresh-seed confirmation was skipped, and no Flywheel promotion receipt exists. No signature verification or promotion is claimed. The baseline fitness is a training-signal measure, not a leaderboard score.

Four task families (office, finance, math and media) scored 8/8 and had zero sampled group reward variation. Native image validation passed, but training readiness of the complete task mix is not established. Before paid training, select a documented task mix with useful reward variation, freeze its exact configuration, prepare and validate the training adapter, and obtain approval for a concrete GPU quote.

Validated runtime: source `088f6e035cb9696ce1128a643ed5a85d21e22144`; public linux/amd64 image `ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:6a656cac9bb519eecc5c34cccb3d296dbc3b2e29e615a5d6af422d0ee08e6a7b`. [CI](https://github.com/nicholas-ruest/openenv-decision-ledger/actions/runs/38306298345) passed 32/32 anonymous native controls. The image is validated, not Darwin-promoted.

[Exact counts, evaluator errors and original report SHA256](darwin-final-decision-2026-10-12.json). Private trajectories and credentials are excluded. Raw records from interrupted/replayed work are not treated as unique independent cases.

No model training, GPU rental, Arena submission or top-10 claim occurred. The private-training readiness document remains a plan, not a tested launcher. This PR remains a draft and is not merged by this decision.
