# Ignore repair prerequisite stages — October 27, 2026

## Observed problem

A fresh native audit of eight seeds per v11 family (1830000–1830007) evaluated 24 fixtures and 78 controlled whole-function repair variants with zero execution errors. These are oracle edits, not sampled model behavior. In ignore-d2, supplying either correct `rule_mode` alone or correct `classify_ignore` alone earned zero on all eight fixtures. Both together earned one. KV had genuine intermediate function-repair rewards (about 0.18–0.61 unless the chosen function covered every seeded defect); release-d4 replaces its single missing planner in one step. This is a dependency plateau, not evidence that the grader is broken.

## Diagnostic implementation

- `software_repair-ignore-d3` supplies correct rule matching and leaves classifier aggregation to implement.
- `software_repair-ignore-d4` supplies correct classifier aggregation and leaves rule matching to implement.
- Both retain the exact independent oracle, cases, full contract, reward formula and interpreter limits. Cases match d1/d2 at a fixed seed. These IDs identify scaffolds, not an increasing difficulty ladder.
- Existing d1/d2 sources and default eight-task training export remain unchanged. No bonus for format or scaffolding, and no artificial execution failures.

The staged tasks are diagnostic candidates. A single remaining missing function can still have internal semantic difficulty; full-function oracle repair succeeding does not establish model learnability or within-prompt variance. This implements a testable alternative to the observed two-function plateau, not a proven improvement.

## Validation and release boundary

16 targeted native/analyzer tests passed, including four fresh disjoint prerequisite seeds (1850000–1850003), matching cases/oracles, zero unchanged rewards, full corrected rewards, no native execution failures and unchanged default export. The earlier diagnostic commit's native-validation CI 40459652010 passed. New runtime changes require their own CI/image validation; this report does not qualify a new image.

The currently qualified source remains `164cb2b1fdd9217093cc7182c1801b571908decc` and image remains `ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:77e34e465b514ef619ad2c02db57451c815bb478cf054eb16ce885516bd3ab7a`. No submitted dataset or approved request was changed. No inference, search, training or submission was launched.

Next: inspect new CI; establish recorded task-name mapping before attributing v11 metrics to a family; evaluate the scaffold hypothesis with matched model calls only after existing spend is reconciled. Do not switch the training mix based on oracle controls alone. Prepare any revised exact request for human approval only after its actual public image is qualified.
