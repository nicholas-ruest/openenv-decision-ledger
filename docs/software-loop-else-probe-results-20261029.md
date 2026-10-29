# Fresh loop-else confirmation: no measured gain

Eight fresh model replies were generated once each and graded unchanged under both the baseline `9d1a28a3357f87349bcbc81166a2c1191c2d03c6` and the compatibility candidate `b3a8873a4629a1cb34d2dfd7b297895783d9af9e`. Both scored **1/8 full solves**, with identical semantic rewards and failure classifications. Full-solve delta and mean semantic delta were both zero. The earlier posthoc execution-to-full replay did not replicate as a gain on this disjoint set. No candidate promotion or model-improvement claim follows.

| Task/case | Replies | Full, each runtime | Partial, each runtime | Execution failures, each runtime | MetaHarness signal, each runtime |
|---|---:|---:|---:|---:|---:|
| ignore-d3 / 2540000 | 4 | 0 | 1 | 3 | 0 |
| ignore-d4 / 2540100 | 4 | 1 | 3 | 0 | 1 |

The d3 partial reward was 0.70. The d4 rewards were 1.00, 0.95, 0.95 and 0.95. Actual unmodified MetaHarness `fitness.mjs:scoreCell` executed over four-sample same-prompt groups. Its d4 signal reflects four eligible answers with mixed rewards; d3 execution failures void purely reasoning-driven group signal. This is a curriculum diagnostic from two procedural cases, not evidence of model learning or private transfer. The upstream checkout was independently verified at `b8c3d38de41203faf633ef6dceb8452a4727b0ea`, with fitness SHA-256 `852da62a33b833bc0a8cbc015891e3030d769b40fa41bf9793da84bdadfff130`.

All eight assigned calls returned independently identified responses with observed usage; no retries or unknown-usage outcomes occurred. The paired runtimes intentionally share each reply, so 16 runtime grades are not 16 model calls. Maximum observed generation was 3,064 tokens, terminal observation 34 tokens, and accounted context 6,159 tokens, within the unchanged 4,096 total completion and 8,192 context budgets. Supervision completed in 632.36 seconds with verified worker shutdown. Model route and thinking were requested identically across the paired grading; production training-wrapper equivalence and provider thinking behavior are not attested.

Driver source: `f453217842e6a5ffed8dd42aafd3fa28b7615b80`; paired assessor: `f20aab360410c3e2295810c44d761f3b94e7b008`; frozen inputs: `dc29f49ddc308f4df4ac194de5955adb41efd69af99090dd8a6a67167ea9e22f`. The assessor rejects scripted archives and requires a complete live archive, bound input digest, unique response identities, matching usage and unchanged raw response hashes before paired grading. It independently recounts terminal observations and context under each runtime. Private paired-result SHA-256: `645c8970ebcfa326366de996b593c48ec5b300a20b54ec1e9a9d089323276572`.

The compatibility candidate passed six focused language tests. Its broad software suite recorded 711 passes and one failure in the pre-existing `test_timeout_stops_descendant_ignoring_term`; that failure was independently reproduced on the unchanged baseline. Broad-suite log SHA-256: `b513391247459262925868dacf28feaa697c5994c59eb37ff4df6372dad932d2`. This is not a clean full-suite qualification or a qualified replacement image. The actual inference caller uses the separate in-process `screen_deadline.run_bounded` supervisor, whose completed worker shutdown was verified.

No Arena evaluation, training, submission, dataset replacement, purchase or frozen reviewed-request change occurred. Public-example self-tracing remains a separate controlled experiment on the unchanged full-module runtime.
