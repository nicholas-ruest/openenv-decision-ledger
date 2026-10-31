# Function-review advice: selected screen, not confirmed improvement

The frozen software screen produced **3/4 full solves with function-review advice versus 2/4 with standard module-review advice**. All eight assigned attempts remain in the denominator. All 14 actual calls returned independently replayed, known-usage replies. This is one procedural case with four samples per arm; it is not a confirmed improvement or a leaderboard result.

| Outcome | Standard module review | Function-review advice |
| --- | ---: | ---: |
| Full solves | 2/4 | 3/4 |
| Valid wrong outcomes | 1 | 1 |
| Native execution failures | 1 | 0 |
| Provider, budget, format or truncation failures | 0 | 0 |
| Successfully applied function-block revisions | 2 | 3 |
| Initially full proposals, measured posthoc | 2 | 2 |
| Failed initial proposals repaired to full, measured posthoc | 1 | 1 |
| Initially full proposals lost during revision, measured posthoc | 1 | 0 |

The nominal full-solve and semantic-mean deltas were both +0.25. The posthoc stage audit suggests retention rather than an additional repair explains the difference: each arm repaired one initial failure, while standard review broke one initially correct proposal during a complete-module final rewrite. Both arms had one first-response schema echo; the frozen parser treated each as an empty action and graded the unchanged module wrong. Those attempts were retained without retries.

Both arms had the same initial prompt and action schema, public field/runtime feedback, public module hash, Native package, sampler and budgets. Both could return complete modules or hash-bound replacement functions. Only treatment review advice encouraged localized function revisions. Control also used function mode, so this screen does not isolate the availability of function edits from their absence.

Screen source: `8de6b520b342c1595dfae003cfe5e6d87114d8de`. The registered gate passed: complete assignments and verified usage, positive full-solve delta, nonnegative semantic delta and actual treatment function-edit use. [The sealed selection receipt](../research/software-function-revision-confirmation-20261030/screen-selection.json) records the aggregate results and input/assessment hashes.

The screen used 50,190 generation tokens in total. Maximum per-attempt generation plus observations was 7,958 tokens; maximum accounted context was 8,243. Limits remained 8,192 and 24,576 respectively. Intermediate feedback used supplied public examples only, and hidden cases were evaluated only for terminal grading and separate posthoc analysis.

The original reserved disjoint confirmation was bound after selection, with source `e3ed902b693cc1669397d7b090d96205c870aa82`. Its environment and app files are byte-identical to the screened method; the Trial, sampler and assignment-schedule ASTs are unchanged. The original reserved job identities are preserved. Its 36 public/hidden inputs have no overlap with 44 earlier materialized or prepared task/seed pairs containing 1,440 distinct inputs. No completed confirmation result is reported here.

Confirmation qualification passed 25 Native/protocol/actual HTTP-WebSocket tests and 10 assessment tests, including selection/assignment lease rejection, forged-audit refusal, independent replay and source-binding checks. Native/protocol log SHA256: `45adf2110823cf227bc9016b89bdaf892e90fa9331b906e1e4cc12c14a7ba305`; assessment log SHA256: `4fa4a5958f04e6b30e5d9f286f692dcb916b48fb18ff5079f08bbc058f0b191c`.

The assessment actually executes the pinned unmodified MetaHarness fitness module, revision `b8c3d38de41203faf633ef6dceb8452a4727b0ea`, through the existing software adapter. This is a bounded inference-policy experiment, not GRPO or model training. No production image was built or replaced. The common Native package retains the previously documented unresolved process-coordinator regression test failure. Arena actor equivalence, transfer and leaderboard gain remain unverified. The frozen v12 request and HF dataset are unchanged; no Arena submission or HF replacement occurred.
