# Bounded bool compatibility: qualification and frozen comparison

The sorted-call runtime still rejected `bool()` in one saved model program. Adding bounded Python truth conversion recovered that saved program. This is posthoc runtime compatibility evidence, not a new model solve or training gain.

| Artifact | Pin |
|---|---|
| Sorted baseline Native source | 34ae9401ec3a9530e2a71916060ea3a4c75eaa72 |
| Bool candidate Native source | bc9a7fab8392c17a6f1d4bf27a6aa50c92df9ebb |
| Frozen paired comparison source | e834c57a7dd16e43771755e047ee6d20bdaaebe3 |
| Baseline runner SHA256 | be2672ea479dc2520af5366b3cad6741e0195497cc6fdea1198232ab40a4e4a8 |
| Candidate runner SHA256 | fcb0f8b5cb5321ae998f71a38502125a595cc39d6b6331eedd659ba9ceed65a6 |
| Compatible financial gate SHA256 | 5e2f25daea0f59c248ab75e22a134b89259c6892d24335f3c9c4a1b807da7e8c |

## Native change and validation

The candidate adds `bool` to the existing bounded builtin dispatcher. Native functions named `bool` retain dispatch priority; a non-callable local variable named `bool` is rejected. Zero/one positional argument truth conversion follows Python behavior; unsupported keyword calls remain rejected. Program execution remains in the existing bounded interpreter, including existing step and allocation limits.

The candidate's bool, sorting, string and tuple checks passed **44 tests with 29 subtests**. The shared-program protocol passed **8 tests**, including separate Native package identities, real executed bool control recovery, exact prompt/request/usage replay, tamper rejection, unknown usage, truncation, financial denial, and all-assignment selection accounting.

Protocol test transcript SHA256: `b4c8e3b79f30dc21314154271abb16e9a1e3cc35b93f1ab10b7731c61dbd2818`.
Focused Native test log SHA256: `fc479f11fae05dc2866d7efe1fc8a385025cabd14e8ccb280725f69361cb8989`.

Broad candidate regression and a production image are not qualified. The sorted baseline's existing full-suite result was 711 passes and one known supervision test failure, also present in its baseline. Those results do not substitute for broader bool-candidate qualification.

## Saved-response analysis

Four existing complete model programs from the failed sorting screen were replayed unchanged through both Native runtimes: baseline **2/4 full**, bool candidate **3/4 full**, with no lost full solve. One actual bool-call failure became full; another TypeError remained. No model calls were made for this replay. Candidate choice used these failures, so the replay cannot establish fresh improvement.

## Frozen fresh screen

One new software ignore-d3 case, seed 3020000, is disjoint by source/examples from 40 prior cases recorded in 104 input artifacts. Four sampled model programs are each graded unchanged by both isolated pinned runtimes. Both have sorting support; only bool support differs. The candidate copies the actual pinned Native package and replaces only runner.py. No model code is executed by the host Python interpreter.

Both grades use the same program, cases, prompt and action schema. Only the baseline terminal observation counts as an observation; candidate analysis is never fed back. Each sample uses one model call with a 6000 generation limit, 8192 generation-plus-observation and 24576 context limits, the same provider route and temperature 0.7, and no thinking override. Generation is charged once per program.

Selection requires four complete known responses, a positive paired full-solve delta, no lost baseline full solves, nonnegative semantic delta and actual execution compatibility exposure. Reserved confirmation seed 3030000 is unmaterialized and cannot be used unless that gate passes. No retries or redraws.

Native controls are scripted qualification checks, not model solves. Any fresh runtime compatibility result remains separate from model learning, Arena-managed GRPO, held-out Arena performance and leaderboard gain. Existing frozen v12 request, runtime image and dataset remain unchanged.
