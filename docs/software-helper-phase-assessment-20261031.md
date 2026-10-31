# Helper controller qualification phase assembly and fitness

The separate helper-preservation candidate now has complete-phase qualification assembly and a controller-aware assessment using the actual pinned MIT MetaHarness `fitness.mjs:scoreCell` at `b8c3d38de41203faf633ef6dceb8452a4727b0ea`. The upstream adapter checks the original source hashes before import. No upstream confirmation or promotion mapping is claimed.

The assembler binds the original eight assignments across four ordered chunks, checks reservation/call/reply identities, and independently replays available Native traces. Semantic rewards come from that replay rather than untrusted summary fields. Controller-assisted full controls and outcomes with no controller action are counted separately. Both remain scripted controls, not model solves.

Missing chunks and stopped failures preserve all eight assigned denominator entries. Uncalled assignments are explicit. Called turns without a verified reply retain unknown usage; their cost is never filled with zero or an earlier reply's cost. A phase with any incomplete or unreplayed assignment gets descriptive counts and no MetaHarness fitness score. Later chunks after a stopped phase are rejected.

Seven focused tests passed on the already-used qualification case. They cover the complete four-chunk assembly and actual fitness invocation, missing last chunk, unknown usage after a known reply, record/identity tampering, JSON key-order independence, refusal to relabel controls as live evidence or pool future cases, and receipt-cost/budget/terminal-reward checks. The key-order regression caught and fixed an identity comparison that incorrectly depended on JSON object insertion order.

The assessment validates reported generation, Native observation and controller receipt costs against the original 8,192 completion limit, with at most two model responses. A semantic result cannot hide receipt cost or replace the independently replayed Native terminal reward. The independent replayer exposes these semantic fields without changing the raw trace's earlier accounting shape.

Reproduce with the pinned Python environment and cached public tokenizer:

```sh
HELPER_TEST_TOKENIZER=/absolute/path/to/tokenizer.json python -B -m unittest discover -s research/software-helper-controller-20261031 -p test_phase_assessment.py -v
```

`phase-assessment-qualification.json` binds this test run's source and log hashes. Earlier adapter and orchestrator qualification manifests are historical snapshots bound to their recorded source revisions; their old test counts are not added to this run's count. This qualification updates the replayer and tests its integration through the full phase.

Every assessment output is explicitly qualification-only, with live evidence, selection, promotion, training, model improvement and leaderboard gain false. Production materialization and paid execution remain blocked. No new model calls, procedural cases or allocation mutations occurred. Production transport, supervisor integration, actual-case admission and an independently attested live-evidence assembly path remain pending. ruOS execution timed out, so current private state and credit could not be reattested. Frozen v12 and the closed finalization study remain unchanged.
