# Retained semantic recurrence check — November 2, 2026

The next saved semantic partial was selected by its existing sample index, rather than by trying the previous representation-loss edit until it worked. This second program **already preserves original rule text** at the helper call boundary. The previous representation-loss mechanism therefore does not recur here.

The unchanged program compiles and terminates on the same six originally supplied public examples, passing **5/6**. It derives directory status from path depth instead of using supplied entry metadata and recognizing implicit parent directories. It also returns early for a directly negated entry before checking ignored ancestors.

Two narrowly scoped entrypoint edits were replayed independently and jointly:

| Correct explicit/implicit directory typing | Remove the child-negation shortcut before parent blocking | Public examples passed |
| --- | --- | ---: |
| No | No | 5/6 |
| No | Yes | 5/6 |
| Yes | No | 5/6 |
| Yes | Yes | 6/6 |

All four variants completed without a runtime error. Helper ASTs and the Native interpreter remain fixed. Neither single edit repairs the final failing public example; both are needed in this saved program. Across this and the preceding diagnosis there are **two programs on one underlying case**, with identical saved public examples, not two independent cases. Parent handling recurs; representation loss was specific to the first program.

**This is investigator-authored posthoc repair, not model improvement, a prospective prompt effect, disjoint confirmation or a leaderboard gain.** The original partial classification, study selection, serving runtime, reviewed requests and dataset remain unchanged. No counterfactual is promoted. Public-example success supplies no hidden-case score.

Executed replay source: `b1cd5479f6a8a3c71e1488ef5117f2bdc7f8ceb8`; script SHA-256 `796700175e3e33f9ca6619aec5aea80cb73092818d48ad531b6fac8bf697969a`. Clean original Native source: `4d69e68c55715d32699f155f068b38a77b8d6d8f`. The replay requires a hash-leased private saved-example report. The initial private extraction matched the original partial record and both completed saved response identities. The replay checks the program hash and exactly reproduces the unchanged diagnostic outputs before comparing edits. It does **not** independently authenticate provider provenance or establish study admission.

Submitted source is AST-transformed and interpreted only by Native Program, never host Python. Raw programs, trajectories, example values and private report identities are excluded from this public evidence. The managed process completed successfully on ruOS. An initial read-only access timeout recovered before replay; no additional worker or retry of paid inference was launched. No new task case, model call or MetaHarness execution occurred. Paid admission remains closed.
