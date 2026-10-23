# Exploratory software runtime variant for human review

[Exact request](../config/software-repair-native-review-20261020.json), SHA256 `fefb7d7c68c7e96c636a84d4a0c9e264fec658bf8db6599182e832669aa0e7bd`, proposes `decision-ledger-software-repair-v4-20261020` at `POST https://openenvarena-arena.hf.space/api/openenv/submissions`. No request has been sent.

It pins source `43b548debcb469af196a282bad07fc3bd8d33b15` and public amd64 image `ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:de25fc0311120f5eac114439fcf13be1b4d4f0bfc98289e29a03db1f013c396d`. CI39511155304 passed 459 tests, 143 anonymous native controls and six SDK checks. Subsequent helper changes do not retarget this frozen request.

The eight train tasks are plan, cover, merge and replay at d1/d2. Release diagnostics are excluded. Each has 12 tool calls, 8,192 generation/observation units, 16,384 context units and a 600-second rollout limit. The JSON contains every field and the full schemas.

The public dataset is `GlobalBusinessAdvisors/openenv-decision-ledger`, observed revision `063900b75ac26423166a80d11e814092b1d05627`. The [typed correspondence audit](results/public-software-task-data-parity-2026-10-20.json) verifies 128/128 identical task definitions between its published source and this runtime: entrypoints, instructions, broken/reference code, public cases and independently generated hidden cases. All 128 published workspaces reproduce from the historical c95e6fe source; all instructions and broken modules also match the current runtime.

Workspace bytes differ: README guidance, visible-test rendering and tool/language features have changed. The HF source archive still describes c95e6fe and its earlier interface. It must not be described as the current runtime. Current source is the public GitHub revision above; the pinned image is the executable artifact. No refreshed HF archive is claimed.

This is a proposed runtime trial over unchanged public task data, with that source/documentation lag explicitly disclosed. It narrows the earlier draft's full matching-bundle update requirement into a specific human review decision. Approval must explicitly accept that lag; otherwise the request remains on hold. The expected dataset revision must be rechecked before any POST, because the API snapshots its head. A changed head or changed body requires renewed review.

No model learning or ranking benefit is established. Proxy release diagnostics failed semantic-signal gating, and they are not the proposed eight-task mix. This is an exploratory Arena measurement, not a Darwin/Flywheel promotion or a top-ten prediction. No merge or new training has occurred.

Reproduce the audit with clean c95e6fe and 43b548d checkouts and the immutable public file software-repair/tasks.jsonl:

```sh
python scripts/audit-public-software-dataset.py --old-root /path/to/c95 --current-root /path/to/43b548d --public-tasks /path/to/public-tasks.jsonl --output /path/to/fresh-parity.json
```

The script verifies source revisions, clean tracked files, the public file hash, typed task equality and correspondence to published workspaces. It performs no upload, inference, credential lookup or submission.
