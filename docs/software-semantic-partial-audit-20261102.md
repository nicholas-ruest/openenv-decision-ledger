# Retained semantic partial: helper input representation

One final program from a closed eight-assignment confirmation was recorded as a semantic partial. On its six originally supplied public examples it compiles and terminates, passing **3/6**. This analysis selects one saved program after observing failure. It does not rerun the model, regenerate a task, inspect hidden cases or change the original study result.

The program normalizes rules into text plus metadata, then sends only the text to an existing helper that expects the original rule syntax. Negation, leading-slash anchoring and trailing-slash directory information are lost at that boundary. Two other entrypoint decisions interact with that loss: inferred parent directories default to file status, and a directly negated child bypasses final ignored-parent blocking.

The diagnostic applies three narrowly recognized AST edits separately and jointly. It changes only the saved program's entrypoint for investigator counterfactuals; every helper AST stays fixed across variants. Original model helper code need not be identical to the supplied starter helpers. The Native interpreter and its resource limits remain unchanged.

| Preserve original rule text at helper call | Infer implicit parents as directories | Apply final parent blocking to every entry | Public examples passed |
| --- | --- | --- | ---: |
| No | No | No | 3/6 |
| No | No | Yes | 3/6 |
| No | Yes | No | 3/6 |
| No | Yes | Yes | 3/6 |
| Yes | No | No | 5/6 |
| Yes | No | Yes | 5/6 |
| Yes | Yes | No | 5/6 |
| Yes | Yes | Yes | 6/6 |

All eight variants completed without a runtime error on these examples. Preserving rule text fixes three original failures but breaks a previously passing example. Both parent-related edits are also needed to repair that regression in this program. This illustrates why retaining a working helper is insufficient when its caller changes the input representation, and why checking the full supplied public suite matters after a repair.

**The 6/6 result is an investigator-authored posthoc repair, not a model solve, a prospective prompt effect, fresh confirmation or a leaderboard gain.** The factorial is descriptive within one adaptively selected program on one already-seen case. It provides no population effect estimate and does not select a new live comparison. Existing failed/partial classifications and study selection remain intact.

## Reproduction and limits

Executed analyzer: `research/software-semantic-partial-audit-20261102/analyze.py` at `1bfe9f73e9adf9777f08559bf27647951d238610`, SHA-256 `ffd37f40ddea0881fa49225531f8e53435ecea0d0f4b0a66cb8cfe7988562e17`. Native runtime: clean original source `4d69e68c55715d32699f155f068b38a77b8d6d8f`.

The analyzer requires the retained private archive. It binds the original record, completed replies, response identities, saved input group and launch source; checks the closure of the original eight-assignment study; and verifies that every archive file it read remains unchanged. It reads assistant action content only, never reasoning. Saved examples are parsed as literals; submitted code is transformed as an AST and evaluated only by Native Program, never host Python. The managed analysis process completed on ruOS and was waited for successfully. An initial exploratory invocation using the system Python lacked the OpenEnv dependency and stopped before the program replay; the configured venv was then used.

Raw programs, examples, trajectories, paths identifying private archives and accounting data are excluded from these public results. Source changes are confined to the offline analyzer and this evidence. No serving runtime, reviewed request, dataset or allocation changed. Actual paid admission remains closed. No MetaHarness module or training loop was executed, and no new model calls or fresh task cases occurred.
