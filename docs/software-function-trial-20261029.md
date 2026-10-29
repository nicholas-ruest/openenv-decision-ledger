# Single-response function-block trial adapter — 2026-10-29

Implemented the missing per-attempt grading adapter for the frozen function-block screen. This is not a provider/paid-call runner and grants no spending, training or submission authority. It does not modify the environment, prompts, sampling settings or reviewed requests.

`NativeBinding` admits only an exact assignment from the frozen screen schedule. It reconstructs the arm-specific initial messages through the existing protocol, checks a fresh native reset against those messages, and requires the caller's expected prompt and problem hashes to match. Confirmation assignments are refused before their observations are generated.

`Trial.consume` accepts one externally obtained raw assistant response. It uses the actual arm's Pydantic action model, including its defaults and extra-field behavior, and the actual unchanged native environment. Both a completed attempt and every format/provider/truncation/execution failure close the attempt before another response could be consumed. Explicit external budget aborts also close it. Length-limited responses are recorded as truncation before grading; unknown provider termination is kept outside semantic outcomes.

For native terminal results, the existing terminal-only auditor distinguishes interpreter failures from valid wrong/partial/full repairs. The baseline wraps its direct environment only for the auditor's attribute interface. Treatment-level invalid function edits receive a separate edit-rejection category. Full-module fallback remains available. Hidden diagnostic aggregates are never appended to the model transcript; no second response or feedback intervention is introduced.

## Verification and limits

Five local lifecycle tests passed against an explicitly fictional binding. They check input-hash rejection, single consumption, no retry after malformed/truncated replies, terminal external aborts, native-contract violations, and exclusion of diagnostic output from messages. These tests do **not** execute OpenEnv, the real grader, a model, or MetaHarness search.

Three native integration tests are included but **have not been run**. They must be executed inside a fresh isolated checkout during permitted ruOS hours before this adapter is used. They exercise actual reference grading in both arms, function-edit rejection versus interpreter failure, and treatment full-module fallback.

From the repository root with native dependencies installed:

```bash
python -m unittest discover -s research/software-function-trial-20261029 -p 'test_*.py' -v
```

Only the local fictional lifecycle subset was executed in this step:

```bash
python -m unittest discover -s research/software-function-trial-20261029 -p 'test_lifecycle.py' -v
```

The complete-phase caller remains missing. It must authenticate immutable input/source/provider records, bind real call and response IDs, reconcile the existing account/receipts, admit the full phase, reserve before each call, account for actual token/context costs and enforce hard deadlines. This module does not implement those mechanisms or replace the older runner. Its result fields still require a durable accounting/identity envelope before software assessment.

No ruOS access occurred after its fixed stop. No new model calls, oracle replays, training, purchases, dataset replacements, submissions, automation or public conversation updates occurred. Fresh model and leaderboard improvement remain unmeasured.
