# Software repair candidate

An isolated candidate for the next Decision Ledger experiment. The first
submission remains unchanged. No private score or trained-model improvement
is claimed for this candidate.

The learner edits `src/solution.py`, runs visible test cases, and submits a
workspace for independently generated hidden cases. Six software families,
two difficulties each, are selected with `software_repair-FAMILY-d1|d2`.
Actions are `list`, `read`, `write`, `test`, and `submit`; write requires the
exact module path. Reading `*` returns all four visible files. Tests give
feedback only on visible cases. Each episode permits12 actions.

Only a documented pure subset of Python is interpreted. No host Python eval,
exec, subprocess, imports, filesystem or network is available to candidate
code. Code may use named functions, assignments, conditionals, loops, literals,
lists/dicts, indexing/slices, bounded integer arithmetic, comparisons,
len/min/max/sum/abs/sorted/list/range, list.append and dict.get. This is not a
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
public GHCR package, independently pulls by digest and exports192 visible task
rows plus the exact image-bound request. These are runtime controls, not model
benchmarks. Neither workflow nor exporter can submit to Arena.
