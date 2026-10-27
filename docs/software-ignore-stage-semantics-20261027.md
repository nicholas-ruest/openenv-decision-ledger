# Ignore prerequisite semantic controls — October 27, 2026

The two prerequisite stages from source f6bf35d482254a45481de8b89cf00730e3aa3d0b now have full native CI evidence: workflow 40465450630 passed all three jobs, 626 tests and 260 anonymous direct-code controls. The tested direct image index is `ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:f613df8d97def3500a28a9911b4bae8ef494b78e4d7e6e4893afb3898643fc10`; its built amd64 manifest is `sha256:fef96cbd85d8ceb0977c2a0f4ee633db5f8f442905affc09616c5583a0775a8b`. This is a tested diagnostic image, not an approved replacement submission. Preserve the v11 rollback image.

## Semantic partial-credit experiment

On fresh seeds 1860000–1860007, 16 fixtures and 56 controlled semantic mutants yielded fractional rewards in all 56 cases, no interpreter/execution errors, and public examples detected every mutant whose hidden cases were wrong. Supplied prerequisite functions were kept identical to the reference AST text; only the function the stage asks the model to implement was changed.

| Stage | Semantic defect | Reward range |
|---|---|---|
| d3 classifier | Parent pruning | .767–.933 |
| d3 classifier | Rule priority | .900–.950 |
| d3 classifier | Implicit parents | .767–.933 |
| d4 rule matcher | Negation | .950 |
| d4 rule matcher | Root-relative slash | .450–.817 |
| d4 rule matcher | Directory-only pattern | .750–.900 |
| d4 rule matcher | Literal leading space | .850–.950 |

These are controlled oracle mutations, not model solves. They demonstrate accessible intermediate credit for semantic errors, not that a model will learn or transfer to the private evaluation. The high rewards on some incomplete repairs may still encourage saturation; the exact full-solve requirement is unchanged. No reward weakening, runtime limit relaxation or evaluation-specific content was added.

## Anonymous replay improvement

The previous anonymous replay's generic partial control was unchanged source for ignore tasks. It therefore tested no actual intermediate reward for these stages. Replay now includes a wrong parent-pruning classifier for d3 and a wrong-negation matcher for d4, and requires strictly fractional rewards through the real native WebSocket API, matched to the local grader. Four exact replay seeds per stage are checked offline first. New replay assertions need their own CI result before claiming they passed remotely.

Reproduce with `python3 scripts/audit-ignore-stage-semantics.py --output /tmp/fresh-stage-semantics.json`. No credentials, inference or submission are involved. Raw public/private procedural fixture controls can be regenerated; canonical raw-record SHA is included in the summary. These fixtures are our generated environment data, not Arena private grading data.

No dataset replacement or Arena POST occurred. A future curriculum using these stages is still a hypothesis and requires an exact reviewed request and explicit human approval.

Local validation: 28 targeted analyzer, repair-path and stage-semantic tests passed, including all eight exact anonymous replay controls.
