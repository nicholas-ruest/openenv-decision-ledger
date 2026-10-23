# Merge witness diagnostic (not adopted)

`software_repair-merge-d3` is a separately registered diagnostic, excluded from
the eight-task training export. It does not replace merge-d2 or the retained
submission review candidate. No model generations, training or submission were
performed for this change.

## Measured problem and fair change

The preceding two-cohort audit found that public merge-d2 examples missed the
isolated touching-flag defect in7 of16 prompts while hidden checks activated it
in all16. Random extra intervals can bridge the intended touching boundary,
making that fault invisible even with `merge_touching=False`.

The diagnostic preserves merge-d2's contract, reference implementation,
independent expected-value oracle, two original AST faults,11 interval pairs,
interpreter/resource limits, action schema and reward formula. It changes only
the procedural case distribution. Disjoint distractors cannot bridge the
witnesses. Random origins, widths, distractor lengths and input order give
independent seeded public/hidden cases.

| Scenario | Original module | Nesting fix only | Touching fix only |
| --- | --- | --- | --- |
| Strict nesting, no touching | Wrong | Correct | Wrong |
| Touching must stay separate | Wrong | Wrong | Correct |
| Nesting plus touching | Wrong | Wrong | Wrong |
| Touching explicitly enabled | Correct | Correct | Correct |
| Invalid/disjoint pairs | Correct | Correct | Correct |
| Duplicate outer plus nested interval | Wrong | Correct | Wrong |

The reference is correct in every scenario. Positive controls are retained:
the broken module passes10/30 hidden cases, but unchanged code still earns0.
On the measured case sets, nesting-only repair passes20/30 and earns0.5;
touching-only passes15/30 and earns0.25. Both fixes earn1. No reward formula or
execution failure is used to manufacture difficulty. Lower/higher constructed
partial rewards are not claims of better model learning.

## Reproduction and limits

```sh
python scripts/audit-software-curriculum.py --seed 1080000 --count 8 --tasks software_repair-merge-d2 software_repair-merge-d3 --output merge-a.json
python scripts/audit-software-curriculum.py --seed 1081000 --count 8 --tasks software_repair-merge-d2 software_repair-merge-d3 --output merge-b.json
```

The two disjoint cohorts contain32 task instances and1,152 reference/oracle
checks. All pass, with no repeated typed input keys, split overlaps, conflicting
labels or execution failures. New diagnostic public examples expose both
isolated faults in all16 instances (32/32 defect controls); old examples miss5
of32 isolated-defect controls. All32 new constructed single-fault repairs earn
partial reward, versus16 zero and16 partial in the old distribution. These are
constructed controls, not model-generated repairs, unique model samples or
training signal confirmation. The two task arms are different case sets, not
identical-prompt causal comparisons. Six scenario templates are not a claim of
unbounded semantic diversity.

## Locked future comparison

The historical offline packet builder now also accepts:

```sh
python scripts/plan-replay-calibration.py --profile merge_compare --output merge-plan.json
```

The runner's `merge_compare` preview uses old/new tasks, two distinct prompts
per task, four independent sampled rollouts per prompt, and at most192 calls
in each1200-second stage. Screen seeds are1082000/1082100; conditional fresh
confirmation seeds are1083000/1083100. They are disjoint from these audits and
the existing training partitions. Only merge-d3 can provide its candidate
signal. The runner rejects `--execute` for this profile before budget,
credentials, tokenizer or provider access. No stage is admitted by this plan.

Keep model, selected provider metadata, route, tokenizer, thinking request,
temperature, JSON actions and budgets matched across arms/stages. Require
identical observed reset/workspace hashes within a sampled prompt, complete
independent call identities, genuine full/non-full valid completions, and
fresh candidate-specific confirmation. Format, provider, truncation, budget
and execution failures cannot supply variance. Local finish diagnostics are
not valid completions. Arena checkpoint/thinking/chat-wrapper equivalence
remains unattested. Frozen old packets must use their original source; new
merge and replay packets record this source revision's actual file hashes.

The next evidence needed is a separately admitted bounded model calibration,
not automatic mix adoption, training, promotion or Arena submission.
