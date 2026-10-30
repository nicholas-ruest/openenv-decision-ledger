# Computed public-example feedback: Native-budget preparation

No model calls have been made for this experiment. Exact tested source: `443189be6d4861d27657237db790839c7dd56e39`.

Nine Native caller/replay tests passed in 18.375 seconds on ruOS, including two-response scripted trajectories, identical first prompts, bounded computed public feedback, independent replay and tamper rejection, unknown second-turn usage, truncation, context overflow, whole-study admission refusal, and actual CLI refusal under the unchanged supervisor. Ten assessment tests passed, including rejection of different first prompts across the computed-feedback arms. These are controls, not model solves.

Native test log SHA256: `52767fc6ae47f6a1bb0d6f9e47d2f1e3fb92f22ff9830af0d2cee436be43af45`. Assessment test log SHA256: `e93e56deaa49eb9d5c57c2ca10e60fbd30230b0102a89efea3044c516219849d`.

The actual MetaHarness checkout was verified as `b8c3d38de41203faf633ef6dceb8452a4727b0ea`; its fitness SHA256 was `852da62a33b833bc0a8cbc015891e3030d769b40fa41bf9793da84bdadfff130`, matching the unmodified hash-checked copy executed by the assessment adapter. No Darwin runner was started.

The separate experiment assigns eight attempts, four per arm, on one frozen ignore-d3 case, in four manually launched two-attempt chunks. Both arms receive exactly the same first prompt and two-response schema. After a first proposal, one receives computed results from the six public examples already visible in the prompt; the other receives neutral review. There is no helper-preservation intervention. A final full-contract grade is required; public-example all-pass alone cannot promote a candidate.

Per attempt: 8192 total completion tokens including all post-reset observations, 24576 context, maximum two responses, and a 600-second rollout wall. First generation is at most 6000; second generation is bounded by the actual remaining total budget, reserving 96 terminal tokens. This split can cause first-response truncation or leave insufficient revision space. It is explicit and matched across arms. Native direct environment observations do not attest production Arena wrapper equivalence or thinking behavior.

Before any model execution, the complete sixteen-potential-call study must fit the existing reconciled allocation, with actual credit observed and every parent/reservation retained. Each call reserves before execution. Unknown usage or provider/budget failure blocks subsequent chunks. Existing 1200-second worker supervision, no-duplicate checks, fresh archives and Toronto operating hours remain unchanged.

The complete eight-assignment screen must have independently verified raw identities, usage and Native replay, a positive full-solve delta, and nonnegative mean semantic delta. Selection must be frozen before fresh disjoint confirmation observations. A screen alone is not an improvement, transfer or leaderboard claim. The one-case sample is small. No training, dataset replacement or Arena submission is authorized by this artifact. Reviewed requests and runtime images remain unchanged.

Source and tests: `research/software-native-feedback8k-20261029/`. The earlier preparation sources were not model-executed: the first test setup referenced an absent path, and the second omitted the arena_env import path. Both archives remain preserved; the exact source above passed the corrected Native suite.
