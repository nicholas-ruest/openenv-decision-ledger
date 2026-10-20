# Software repair candidate

An isolated candidate for the next Decision Ledger experiment. The first
submission remains unchanged. No private score or trained-model improvement
is claimed for this candidate.

The learner edits `src/solution.py`, runs visible test cases, and submits a
workspace for independently generated hidden cases. Ten software families,
two difficulties each, are selected with `software_repair-FAMILY-d1|d2`.
Actions are `list`, `read`, `write`, `patch`, `test`, and `submit`; write requires the
exact module path. Reading `*` returns all four visible files. Tests give
feedback only on visible cases. Each episode permits12 actions. Reset already
includes the README; a direct source read avoids repeating it. Test feedback
keeps two failing expected/actual results; all six complete input examples
remain available in the visible test file.
Each detailed failing result includes a `case_path` such as
`tests/test_public.py#case=2`. Reading that view returns exactly that public
example's input and expected output, with no hidden-case access. The complete
test file and read-all action remain available.

Only a documented pure subset of Python is interpreted. No host Python eval,
exec, subprocess, imports, filesystem or network is available to candidate
code. Code may use one to four top-level named functions, assignments, conditionals, loops, literals,
lists/dicts, indexing/slices, bounded integer arithmetic, comparisons,
bounded comprehensions, break/continue, len/min/max/sum/abs/sorted/list/range,
set/dict/tuple/enumerate/zip/any/all, list append/pop/sort/reverse/remove, set.add/remove/discard,
and dict get/pop/items/keys/values. Source is capped at8192 bytes, collections
at128 items, and interpreter work at80000 steps per test case. This is not a
shell or an arbitrary Python execution sandbox.

Rewards require improving hidden behavior over the original broken code.
Unchanged/comment-only code earns0; all hidden cases passing earns1; partial
improvement is capped0.95. Invalid/unsupported code earns0. A submitted workspace
is terminal, and test/README files are not writable. See [ADR0002](../../docs/adr/0002-software-repair-candidate.md).

From the repository root, with the existing pinned runtime/test environment:

```bash
python -m pip install -r integrations/openenv-arena/requirements.lock -r integrations/openenv-arena/requirements-dev.lock
PYTHONPATH=integrations/software-repair python -m pytest integrations/software-repair/tests -q
PYTHONPATH=integrations/software-repair python -m uvicorn repair_env.app:app --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
openenv validate --url http://127.0.0.1:8000
python integrations/software-repair/scripts/replay_native.py --url http://127.0.0.1:8000 --output /tmp/software-repair-replay.json
docker build --platform linux/amd64 -f integrations/software-repair/Dockerfile -t software-repair:candidate .
```

The GitHub workflow additionally publishes an exclusive tag in the existing
public GHCR package, independently pulls by digest and exports128 visible task
rows plus the exact image-bound request. These are runtime controls, not model
benchmarks. Neither workflow nor exporter can submit to Arena.

The initial four-prompt target-model screen solved all16 rollouts, with zero
within-prompt variance. Those basic families remain available as diagnostic
controls but are excluded from the default proposed training mix. The current
export selects eight provisional harder tasks: dependency build plans, minimum
cost regression-suite selection, interval merging and idempotent event replay,
each at two levels. A fresh bounded screen must establish whether these offer
useful reward variation. This is still one software category, and neither the
interface nor these synthetic tasks are attested to match private evaluation.

Test feedback reports every case status but repeats detailed input/expected/actual
for at most two failures, avoiding large successful-test payloads. Full visible
examples remain readable in the test file. The proxy permits all12 environment
actions and still independently enforces its token/context and dollar caps.

An additional diagnostic task software_repair-plan-d3 adds induced-subgraph
cycle components, downstream blocking, unknown changes and stable incremental
ordering. It is excluded from the default export until model signal is tested.
There are24 available IDs, with120 native controls including exact-text patches. Bounded lazy generator
expressions support short-circuiting and at most128 yields; single-underscore
helpers/locals,16-deep calls, bounded copy/extend/update and set union/intersection
support natural algorithms without granting host Python access.

The cycle-aware task now starts with a complete but broken planner containing
local ordering/deduplication defects. It is a debugging task, not implementation
from an empty stub. Offline controls verify that an incomplete semantic repair
earns partial credit and the complete repair earns1, without interpreter errors.
These controls are not model rollouts or learning evidence.

The earlier empty-stub screen is archived separately: two valid full solves over
eight rollouts/two prompts, four provider timeouts, one truncation and one episode
budget failure. It did not qualify for confirmation. The new scaffold has not
yet been screened against the model. The historical submission JSON and Hugging
Face preview still pin the earlier image; neither is approved for submission.

The patch action edits one exact nonempty occurrence using search/replacement
fields. Ambiguous/missing matches, protected paths and oversized UTF8 results are
rejected atomically. Patching uses the same interpreter and source-byte limit as
full-file writes. This permits local fixes without generating a complete module;
whether it improves model rollout reliability still requires a fresh screen.

An additional diagnostic software_repair-plan-d4 deterministically varies three
semantic defects across six mutation classes. Its contract and independent
oracle match the cycle-aware planner. Visible examples cover selected graph
shapes; hidden cases also require reasoning about multi-module cycles. The
contract explicitly states that examples are incomplete. Initial defects are
checked for valid execution and useful passing/failing cases, rather than
resource or syntax failures. Existing measured d3 instances remain identical.
The new task is excluded from the default export pending a fresh model screen
and disjoint prompt confirmation; offline mutation controls are not model solves.

Diagnostic software_repair-release-d1 combines that graph contract with
budget-constrained regression-suite selection. Only buildable modules need
coverage; the objective orders uncovered count, total cost, suite count and
lexicographic IDs. Zero-cost suites, insufficient budgets and blocked modules
are explicit contract cases. Six suites bound exhaustive selection to64 subsets.
An independent combinations oracle checks the fixture's bitmask algorithm.
This diagnostic also remains excluded from the default eight-task export.

Diagnostic software_repair-replay-d3 retains replay-d2's two semantic faults,
contract, independent oracle, reference algorithm and18 events per case. Its
examples and hidden pool cover isolated undo defects, isolated duplicate-ID
defects and their interaction. The old pool combined both faults in every case:
fixing either one alone earned zero. In two disjoint offline seed cohorts, each
single-fault repair instead earned1/3 or0.5 on the new pool. These are constructed
repair controls, not model rollouts or evidence of learning. The reward formula,
interpreter limits and default eight-task export are unchanged. This diagnostic
requires a fresh model screen and disjoint confirmation before mix adoption.
