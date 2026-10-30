# Separate interpreter compatibility checks, October 30

The completed real-model joint-task screen at source96fbe8a40b22dbf44ffc652335c0e971cfa48a4a produced zero full solves out of four attempts in each arm. Its sixteen calls all returned auditable replies. Selection failed; no disjoint confirmation observation was materialized. See [screen results](software-joint-public-review-off8k-results-20261030.md).

Two separate compatibility candidates were tested against those same saved responses. These are posthoc replays of sixteen responses/eight final attempts from **one underlying case**, not fresh model generations or independent confirmation.

| Separate candidate | Exact source | Full final solves before/after | Replay finding |
|---|---|---|---|
| list.sort key/reverse | 56e087347005c089fdfe4b284944e905efa34613 | 0/8 → 0/8 | Two syntax rejections became partials; neither passed all public examples. |
| bounded isinstance type predicates | 0bcb0562020001677ca595072076bf475726a437 | 0/8 → 0/8 | All final rewards and error counts unchanged; the localized type check progressed to a candidate TypeError. |

Both branches start from e0c024f03e885bb98429274f6cee03dc3f42dd28, whose runner has SHA256 fbb86c7e594ad50a45a7b3858d8108f4961f075f6795ecb3172fce3c50194764. They are not combined. No inference, helper restoration, extra review turn, diagnostic feedback or reward-rule change was added to these replays.

## Sort compatibility

The two recovered final programs previously used unsupported list.sort(key=...) syntax. One uses a lambda, the other a named key. The new language contract permits that exact bounded feature; the original prompts prohibited keywords/lambdas. The replay therefore does not mean those responses complied with their original contract.

| Recovered final program | Native component-improvement reward | Full public cases passed | Full hidden cases passed |
|---|---:|---:|---:|
| Neutral-review sample | 0.7666666667 | 0/6 | 2/30 |
| Public-feedback sample | 0.8 | 1/6 | 5/30 |

These partial rewards measure repaired semantic components relative to the initial program. They are not solve rates or fractions of fully passed cases. The other six final rewards/error counts remain unchanged. Source, AST, collection, string, execution-step and call-depth limits and input-mutation protections remain.

Eight trusted static CPython/boundary tests passed on ruOS. The existing integration suite reported **711 passed, one failed**, with nine warnings. Its failing test, test_paired_process_coordinator.py::test_timeout_stops_descendant_ignoring_term, immediately checks a descendant's /proc state after termination. The same unchanged test reproduced the same failure on the screen's original96fbe8a source. This is a baseline process-state race; the full suite is **not green**, and no new runtime image is qualified here. An initial unittest-discovery invocation was invalid for this pytest suite and its import-error log was retained; the reported integration result uses pytest with the declared module paths.

Candidate runner SHA256: f0e43ceadc7db6a63a536652bae9f7c64bda8021316cf305976ec5dc0bb9932f.

## Separate type-predicate compatibility

A bounded trace of the third final execution failure on a supplied public example identified isinstance(value, tuple). The old interpreter evaluated tuple as a first-class argument and rejected it as an unknown variable before dispatching the unsupported isinstance call. This was a language-contract limitation, not sufficient evidence of an undefined identifier in the candidate.

The separate type-predicate branch permits only static, unshadowed bool/int/str/list/tuple/dict/set tags, including nested tuples, in the second argument of isinstance. Type objects remain internal and never become program values. It retains the original no-keyword/no-lambda policy and does not add sort-key support.

Fifty-eight selected CPython/boundary/native tests passed on ruOS, with124 deselected and eight subtests passed. This includes the eight new type-predicate tests. No full integration-suite pass is claimed for this branch. Replay rewards and error counts were unchanged for every final response. On the localized public example, the predicate now runs but the candidate later raises TypeError because it calls len on a boolean. It still fails all thirty hidden cases.

Candidate runner SHA256: a887356fad90108e30f1df1be5ce678b8ae03f4154b1f8bbf4524583af81586e.

## Reproduction and limits

The portable replay_saved.py helper accepts --baseline-root, --candidate-root, --archive and a fresh --output path. It parses archived provider JSON, preserves empty-final-content retention, and evaluates candidate text only with the bounded interpreters. It uses the same original task fixtures and reward rule for both versions and independently checks accepted results through DirectRepairEnvironment. It binds all eight event/record files and both runner files by SHA256. Saved private trajectories and cases are not published.

Only authored static test literals run in host CPython; no model response goes to host eval, exec or subprocess. Sanitized qualification/log hashes are in the companion JSON. No study is pooled with earlier screens; no combined compatibility intervention was tested. Neither candidate is promoted. Fresh disjoint matched model evaluation and confirmation remain necessary for improvement claims, with Arena held-out evaluation necessary for leaderboard claims. No training, submission, HF replacement or image replacement occurred.
