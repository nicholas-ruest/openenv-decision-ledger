# Fresh-instance software calibration

Runtime remains frozen at4b6f758ef5f1e345577cf8e74aaa22b89687675a.
The existing repeated-prompt screen and its gate are preserved unchanged.
This additional protocol addresses a specific mismatch: the Arena guide selects
five fresh instances per update and uses the first four valid completions.
Repeated samples of two identical prompts do not cover that instance variation.

`scripts/repair-fresh-group-screen.py` reuses the frozen episode/provider,
accounting and worker supervision code. Two groups each launch five distinct
software_repair-kv-d2 instances, at1152000–1152004 and1152100–1152104.
The first four valid completions in observed completion order are selected,
not the four best rewards. All five records are retained. No retry/replacement
is permitted. Both groups need four valid selected rewards including a full
solve and a genuine semantic nonfull result. Provider/format/truncation,
unsupported code and execution failures are excluded, not called wrong answers.
This conservative validity rule is not attested as the Arena implementation.

Conditional confirmation uses1153000–1153004 and1153100–1153104. All seeds
are disjoint from the earlier repeated-prompt screen, its confirmation,
the fixture splits and preparation controls. Both stages retain the primary
screen's exact model, route, requested thinking, JSON format, temperature,
token/context capacity and360s request limit. A stage has at most ten single
model calls, no retries and a1200s whole-worker bound. Existing append-only
private reservation accounting is shared; no new purchase or allocation reset.
Do not admit this stage while another model worker is live.

This is prospective calibration, not model tuning or an Arena submission.
Passing a screen requires independent fresh confirmation; even that would
establish a sampled learning opportunity, not trained improvement or rank.
The hosted checkpoint/thinking/chat wrapper remains unattested. Source files,
provider quotes, prompt hashes, call identities and completion order are saved.
