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
it anonymously, run pinned `openenv validate`, replay48 controls, and export
visible dataset rows plus the exact candidate request. Export never submits.

The candidate changes both workflow and problem distribution; it is exploratory
and cannot isolate which change causes an outcome. It does not confirm Arena's
private interface. No target-model calibration or training has yet been done
on this candidate. Controls/oracles are not model solves. Target signal and
transfer require further evidence. No private GPU/inference job, new purchase,
automatic promotion, merge or Arena POST is part of these offline gates.

Any next submission requires explicit approval of its exact request. A public
dataset card/export must describe this candidate before that submission; the
existing dataset remains the first-run baseline until such an update is made.
