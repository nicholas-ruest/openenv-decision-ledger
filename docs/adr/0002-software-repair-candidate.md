# ADR 0002: Evaluate an edit/test workflow as the next software candidate

Status: candidate; no promotion, submission or target-model improvement claim.

## Problem and evidence

The first Arena run `9f129154f9335c7e21f4dd6e` completed 291 updates and scored
3/40, including software 0/5. The public untrained reference scored 4/40,
including software 0/5. A single evaluation does not establish a causal effect.
The original `software_change-d2` environment trained one-shot dependency-graph
and suite-selection answers, using list/read/submit. It offered no code editing,
test execution feedback or opportunity to repair an implementation.

All 291 public training metric rows were retrieved on October19. Mean reward
was 0.20447; first-quarter mean0.20660 and last-quarter mean0.21181. Reward
standard deviation and gradient norm were positive on189/291 steps, with
zero-variance groups on102/291. Thus the run had a usable optimization signal,
but these unpaired quarter summaries do not demonstrate task learning.
One step reported a retry. There was no recorded run or cleanup error.

`completions/clipped_ratio` averaged0.99828; the largest logged
`completions/max_length` was165. Do not infer 8192-token exhaustion from a
clipping metric alone or infer effective thinking/chat settings from lengths.
The production trainer version, stop-reason semantics and mask configuration
are not attested by these metrics.

Public evidence:

- [Official leaderboard](https://openenvarena-arena.hf.space/api/leaderboard)
- [Exact run dashboard](https://openenvarena-training.hf.space/?project=GlobalBusinessAdvisors&runs=9f129154f9335c7e21f4dd6e)
- [Final first-run record](https://github.com/nicholas-ruest/openenv-decision-ledger/pull/2#issuecomment-6267528648)
- [Arena guide and interface contract](https://openenvarena-arena.hf.space/AGENTS.md)

## Decision

Keep the first submitted runtime and request immutable. Add a separate
`integrations/software-repair` candidate. It has six original repair families
(clamping, interval overlap, chunking, stable deduplication, counting and prefix
sums), each at two difficulty levels. This is still one software category.

The workspace offers read/write/test/submit. A learner can inspect a broken
Python module and visible test file, edit the module, run visible tests and
submit the repaired workspace for hidden tests. Only the module is writable.
Hidden case inputs come from an independent seeded stream and are disjoint from
visible inputs. No private Arena evaluation data is used.

Rewards measure improvement over the original broken module on hidden tests.
Unchanged, formatting-only and non-improving edits receive zero. Full reward
requires every hidden case; partial improvements receive proportional credit
capped below one. This prevents credit for tests the original already passed.

Candidate source is interpreted, not executed by host Python. The documented
subset has limits on source size, AST nodes, collections, integer magnitude,
call depth and execution steps. Imports, general attribute access, reflection,
filesystem/network access and host subprocesses are absent. This is a bounded
repair workbench, not a real shell or full Python implementation. A real
terminal would require a separate isolation design and review.

## Validation and promotion

Gate syntax/value resource bounds; zero-reward and unchanged-code controls;
independent trusted reference answers; nontrivial partial repairs; hidden/public
separation; session isolation; and every task ID over native WebSocket.
Publish an immutable amd64 image only after tests. A separate runner must pull
it anonymously, run pinned `openenv validate`, replay four controls per task ID (currently80 total), and export
visible dataset rows plus the exact candidate request. Export never submits.

The candidate changes both workflow and problem distribution; it is exploratory
and cannot isolate which change causes an outcome. It does not confirm Arena's
private interface. The initial target-model proxy screen solved16/16 samples across four
unique prompts (four samples per prompt); every group had zero reward variance.
This is inference calibration, not training. It rejected the basic families
as the default proposed mix. Four harder software contracts were added:
transitive build planning, cost-optimal regression selection, interval merging
and idempotent event replay. Their two levels form a provisional eight-task
export, pending fresh target-model signal checks. Controls/oracles are not model solves. Target signal and
transfer require further evidence. No private GPU/training job, new purchase,
automatic promotion, merge or Arena POST is part of these offline gates.

Any next submission requires explicit approval of its exact request. A public
dataset card/export must describe this candidate before that submission; the
existing dataset remains the first-run baseline until such an update is made.

## October19 proxy outcomes and final review status

| Screen | Unique prompts | Samples | Full solves | Failures |
| --- | ---: | ---: | ---: | ---: |
| Basic families |4|16|16|0|
| Harder families, six-action proxy |4|8|3|5|
| Compact feedback, twelve-action fresh plan prompts |2|4|3|1|

The five harder-screen failures were two tool-budget endings, two episode
budget endings and one provider timeout. The follow-up failure was a provider
timeout. Do not turn those zero rewards into genuine wrong answers or useful
GRPO variance: every valid completed sample earned full reward. The three
screens differ in tasks/seeds/runtime and must not be pooled as a benchmark
or interpreted as a paired improvement estimate. Thinking was requested but
not attested; production wrapper/checkpoint equivalence remains unknown.

Successful-test feedback now reports case statuses without repeating all
inputs/answers; at most two failed examples retain details. On the same saved
plan fixture, success content fell from3892 to379 bytes. All visible examples
remain in the readable test file. This is a payload measurement, not a model
performance effect. The proxy now permits all12 environment actions.

A final lexical-loop guard rejects break/continue outside a lexical loop,
including helper calls from inside another function's loop. Source
`c95e6fe79e44c9b1514fd59e186a0a70ac424858` passed109 tests. Replaying all20 saved
action transitions from the four follow-up rollouts reproduced observations
exactly; this replay adds no independent model samples.

The default eight harder task IDs remain provisional. They are an exploratory
software curriculum, not a confirmed productive GRPO mix or a promoted
Darwin winner. There is no second Arena training/evaluation result. The exact
image-bound request is published for review and is not sent automatically.
Each Arena submission still requires explicit human approval. No private GPU
rental or additional credit purchase is needed or authorized by this record.

Evidence: [basic screen](../results/software-repair-basic-screen-2026-10-19.json),
[hard screen](../results/software-repair-hard-screen-2026-10-19.json),
[feedback screen](../results/software-repair-feedback-screen-2026-10-19.json),
[archived replay](../results/software-repair-archived-replay-2026-10-19.json).
