# Software scaffold proxy screen — 2026-10-27

The actual frozen proxy screen completed with **12 full and four valid partial repairs from 16 independent calls**, no format/provider/truncation/execution/budget failures. This is four prompt groups across only **two underlying procedural cases**, not 16 unique tasks.

| Task | Seed | Four rewards | Population reward std |
|---|---:|---|---:|
| Classifier prerequisite (ignore-d3) | 2180000 | 1, 1, 1, 1 | 0 |
| Classifier prerequisite (ignore-d3) | 2180100 | 1, 1, .916667, .95 | .035355 |
| Rule prerequisite (ignore-d4) | 2180000 | 1, .866667, 1, 1 | .057735 |
| Rule prerequisite (ignore-d4) | 2180100 | 1, 1, 1, .95 | .021651 |

Three groups meet the frozen screen definition: four valid samples, at least one full and one non-full outcome. This provides provisional within-prompt reward variation, not fresh-seed confirmation or model improvement.

## Evidence verification

Implemented `scripts/verify-software-scaffold-archive.py`. Fresh frozen native resets, visible workspaces and hidden case identities match the captured archive. Actual initial model messages match the preflight prompts. All normalized rows rebuild exactly from raw records; the assessor verifies the complete expected sample set and independent call/response identities. Each observed call matches its existing reservation. All 16 saved valid actions replay to the exact live rewards and hidden wrong/error counts.

The verifier additionally runs a posthoc component-preservation diagnostic. Four completions changed at least one supplied complete function. One partial classifier repair (.95) had changed supplied `rule_mode`; restoring the supplied function yields reward1. The other changed partial rule repair stays .866667 after restoration. Two full completions also changed supplied functions without harming these cases. AST differences alone are not proof of a semantic defect. These replays are **not additional live model solves**.

Remaining semantic errors include ignored-parent propagation, escaped comment literals and double-star matching. All partial repairs execute successfully; semantic mistakes are not format or infrastructure failures.

34 focused offline tests passed across the runner, phase admission, assessor and archive verifier, including tampered records/reservations and supplied-function restoration. Actual archive verification also completed successfully on ruOS. No new MetaHarness search or Flywheel promotion was run.

## Decision and next comparison

Keep v12 frozen and unapproved. No joint-task model baseline was sampled, so this screen cannot establish scaffold superiority or transfer. The samples are highly solved and partial scores are close to1. No disjoint confirmation has run. Proxy checkpoint, thinking behavior and Arena wrapper equivalence remain unattested.

Next independently tested alternative: a system-instruction comparison asking the model to preserve supplied complete helpers and implement only the missing function unless a concrete contract conflict requires change. Freeze baseline instructions, task instances, provider/settings and independent call identities; use disjoint confirmation cases. Do not ban valid alternate implementations or alter scoring to force variance. This is a hypothesis supported by one diagnostic repair, not an established prompt effect. No paid follow-up is launched here; existing admission/accounting guards still apply.

The reviewed request, runtime and image remain unchanged. No Arena POST, dataset replacement, model training, ranking gain or promotion is claimed.

See [sanitized machine-readable report](results/software-scaffold-screen-20261027.json). Original raw archives and ledgers remain preserved privately.
