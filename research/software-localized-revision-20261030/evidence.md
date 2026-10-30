# Localized revision advice, separate controlled candidate

Execution source: `4bc48b08f2a5aa0cece725f9907e2b84b5f2c537`. No model result or runtime-image qualification is claimed.

Earlier model screens continued to produce incorrect final modules after public-example feedback. This candidate tests whether a revision preference for literal replacements helps retain unaffected code. Both arms receive the same first prompt, action schema, public field feedback, and parent-directory contract reminder. Both can submit a complete revised module, up to four literal replacements, or retain the proposal; no representation is artificially unavailable to the control.

Only the review-turn advice differs: prefer a complete module versus prefer literal replacements. Each replacement must match exactly once in the current module. A bounded sequential transaction is fully validated before any write, and the resulting module remains limited to 8192 characters. No arbitrary code execution is introduced.

The native grader, task contract, hidden cases, interpreter, provider route, sampling, two-response limit, 8192 completion-plus-observation limit, 24576 context limit, and existing reservation gate remain unchanged. Thinking is disabled on both requests in both arms. The first response receives zero reward and never submits to hidden grading.

Frozen screen seed 2840000, reserved disjoint confirmation 2850000; four assigned attempts per arm in alternating order. Confirmation observations remain unmaterialized. Selection requires all eight assigned attempts, independently reconstructed requests/replies/native grading, known usage, no provider or budget failure, positive full-solve difference, and nonnegative semantic difference. No retries, redraws, pooling with previous screens, or redesign on confirmation.

Qualification on the exact source: 23 native/protocol tests and 10 assessment tests passed. Tests cover atomic exact-match edits, ambiguous actions, full-module fallback in both arms, native restoration of a deliberately renamed reference entry point, no hidden grading on the first response, actual frozen scope, accounting and failure-denominator behavior. These are scripted controls, not model solves.

Native log SHA256: `30861f6ef206352db6f9805d1fe29d5db66877efcd2995c5f8993463e8fd2113`.
Assessment log SHA256: `7578ed428072dc94764328537922a92dce73852cf1c1fa2d567120ee7e47d803`.
Unchanged reservation gate SHA256: `5e2f25daea0f59c248ab75e22a134b89259c6892d24335f3c9c4a1b807da7e8c`.

No paid execution is admitted by this document. Fresh private accounting and actual worker inspection are required before launch. Frozen v12 and rollback v11 are unchanged. No Arena POST, HF replacement, training, or leaderboard gain is authorized or claimed.
