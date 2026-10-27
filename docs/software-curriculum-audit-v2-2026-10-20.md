# Offline software curriculum audit v2

This is an environment diagnostic, not a model evaluation, training result or
submission request. The default eight-task export and environment runtime are
unchanged. Replay-d3 and the plan/release diagnostics remain separate.

Reproduce the first fresh cohort with:

```sh
python scripts/audit-software-curriculum.py --seed 1074000 --count 8 --output cohort-a.json
```

The second cohort uses seed1075000 with count8. These procedural seeds do not
replace the predeclared live calibration prompts or train/validation/test seeds.
The script refuses an existing archive, makes no model calls, and records its
exact source hashes. A source revision records the parent checkout when run
with local changes; use the recorded source hashes for exact reproduction.

## Content identity rather than seed identity

The existing task fingerprint includes its seed and source comment. Audit v2
also compares typed case content and seed-independent suite signatures:

| Measurement | Meaning |
| --- | --- |
| Case key | Reference-AST contract, entrypoint and typed argument content |
| Label key | Typed expected value, ignoring dict key order like the grader |
| Suite signature | Reference contract, initial AST, and sorted public/hidden case and label keys |
| Cross-seed duplicate | The same case key occurs under more than one seed |
| Public/hidden overlap | A case key appears in both splits anywhere in the measured cohort |
| Label conflict | The same case key has different expected-label keys |

Booleans and integers, and lists and tuples, are distinct. Input mapping
insertion order is preserved because candidate code can observe it. Seed and
source comments are excluded from suite signatures. The signatures do not
prove program equivalence up to renaming, identify observed model prompts, or
validate provider sampling independence. Reuse between difficulty levels is
reported rather than automatically called leakage. A finite cohort with zero
duplicates does not establish uniqueness over the generator's entire domain.

## Public detection of individual defects

Compound broken modules can fail a public example even when that example does
not expose every underlying defect. For each catalogued local edit, the audit
constructs a module with that defect left in place and every other catalogued
edit fixed. It applies fixes at the unique original defect sites; it does not
invert repaired text, which can occur at several correct sites in planner-d4.

It reports public semantic detection, hidden semantic activation, and cases
where hidden tests activate a defect but public examples miss it. Wrong answers
are separate from interpreter/execution errors. Empty-stub component controls
are not relabelled as isolated local defects. A missing witness is a diagnostic
to review against the full contract, not an automatic reason to alter rewards,
add resource failures or adopt a task into training.

Reference implementations still run through the bounded interpreter against
independently generated expected values. Constructed partial repairs are not
model-generated actions and cannot establish within-prompt learning signal.

## Observation overhead

Per-instance byte counts reproduce the content strings returned by source-only,
read-all and individual-public-case reads. A native regression compares these
strings with the real environment. Counts exclude the observation envelope,
chat template and tokenizer. They are not token-budget admission estimates.
Read-all repeats the README already present in reset; source-only reads and
individual case views are available without removing examples or hiding the
contract.

No paid inference, model training, mix promotion or Arena submission is enabled
by this audit. Any future model comparison remains subject to its frozen
candidate-specific, fresh-prompt and independent-call gates.

## Measured outcome

The two cohorts cover192 task instances and6,912 reference/oracle cases, with
zero repeated typed input keys, split overlaps or conflicting labels across
the combined measured cohorts. All reference cases pass. The448 constructed
partial-repair variants and320 isolated-defect controls had no execution errors.

Public examples miss30 of308 hidden-active isolated defects. The most direct
provisional-task finding is merge-d2's touching flag: public tests miss it in
7 of16 prompts, though hidden tests activate it in all16. Separate diagnostics
also miss some ordering and inclusive-budget defects. The release suite-tie
mutation is hidden-inactive in all12 prompts where it was selected. Those
counts are not model success rates or rollout variance.

The next fair generator review should prioritize explicit touching/non-touching
witnesses without weakening the oracle or introducing execution failures.
Planner and release diagnostics remain excluded from the provisional mix.
No generator or reward change is adopted by this report.
