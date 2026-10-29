# Offline media subtitle reproduction and worker supervision — 2026-10-27

## Media

Added `scripts/audit-media-subtitles.py`, an independent control harness against the attributed public MIT source `proffesor-for-testing/openenv-qe-arena@958198e55299eb18ad812f438a6b2ca6abaa7f5c` (copyright2026 Dragan Spiridonov). It checks hashes of the three upstream skill implementation files before importing them; no copied upstream implementation is embedded.

Actual result:16 fresh subtitle-d2 fixtures (seeds2220000–2220015), all reference outputs reward1, all96 applicable wrong-method controls reward0, empty answers reward0, no duplicate visible case hashes. Visible files total655–909UTF8bytes per fixture. The upstream grader is binary; these results do not establish model reward variance. No model calls.

The previously run15 upstream media tests passed. Full terminal test collection in the local environment failed with `ModuleNotFoundError: No module named 'openenv'`. No terminal test is claimed as passed and no container/isolation qualification is inferred. Next reproduce those tests in an isolated environment with the pinned OpenEnv and required sandbox dependencies, rather than mocking away the import.

## Software process supervision

Added `integrations/software-repair/scripts/paired_coordinator.py`: counterbalanced32-job schedule, admission/deadline checks, persist-before-next ordering and fail-stop behavior. The isolated-worker adapter reuses existing `training.lifecycle.bounded_worker` process-group cleanup. It discards worker stdout/stderr and does not put environment/argv contents into reports.

**12 coordinator tests passed**, including actual subprocess success, nonzero exit and timeout, plus a descendant that ignores SIGTERM. Deadline cleanup stopped the descendant; a zombie is considered stopped, not an active worker. Tests also verify no launch on invalid/expired deadline or missing admission, stop after fatal failure, and no retry after a persistence error.

The core is not a complete paid runner. Whole-phase billing/reservation admission, raw output archive validation and normalization, provider-call wiring and result persistence still need integration. The adapter does not stop remote provider billing or prove a cancelled call was free. No paid process or model call was launched.

## Continuation

Media remains a provisional second category, independent of software/v12. A narrow public-recipe question was sent to the verified swarm thread; the targeted searches in this work interval found no reply. No private Slack content is published here.

Next: reproduce terminal media controls with real pinned dependencies, then prepare a separately attributed media adaptation. Finish software coordinator accounting/archive integration before contemplating any model comparison. Existing caps/approval boundaries remain unchanged. No training, model gain, ranking gain, HF replacement, Arena submission or promotion.
