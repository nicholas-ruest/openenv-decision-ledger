# Separate function-block native app — 2026-10-28

The one-response helper-preserving candidate now has its own OpenEnv application binding, `research/software-function-edit-20261028/function_app.py`. It does not retarget a reviewed server. The existing candidate implementation, full-module alternative, grader and frozen comparison protocol are unchanged.

Source: `2279ecebb0adc296e5f46e784780dc2261e6cd4f`.

## Verification

On ruOS, the seven existing candidate unit tests and five new native-app tests passed. The app tests exercise nine scripted WebSocket episodes: both prerequisite tasks in both action modes, an additive-helper repair, rejected host code, empty terminal submission, and two concurrent sessions with separate task/terminal state. HTTP `/schema` matches the actual Pydantic action and observation models. Reference controls retain native reward 1; invalid/empty controls terminate at zero.

These are real OpenEnv in-process HTTP/WebSocket exchanges through FastAPI TestClient. They are not TCP, Docker, anonymous registry or Arena qualification. No image was built and no runtime image was replaced.

Canonical full schema SHA-256: `ad18a36a169bdf4d585bae93067f7b4c4f0cb855b83298ecafb0693297852855`. This full schema fingerprint includes server state; a future submission must use the guide's required action and observation fields.

## Reproduce

From the pinned repository root with the existing OpenEnv dependencies:

```bash
PYTHONPATH=integrations/software-repair:research/software-function-edit-20261028 python -m unittest discover -s research/software-function-edit-20261028 -p 'test_function*.py' -v
```

The adjacent JSON records source fingerprints and measured counts. The commit changes only the separate app binding and its transport tests. This step does not execute MetaHarness search, call a model, train a policy, or establish improvement.

## Limits and next decision

Fresh model screen and disjoint confirmation remain unexecuted. The function-block protocol has different action instructions/schema across arms by design; it is a matched-problem affordance test, not an identical-prompt test. Public-example feedback remains a separate candidate. No further candidate tuning from old responses occurred in this step.

All reviewed requests remain unapproved. No dataset replacement, submission, new automation, or public-channel conversation update occurred. Actual model comparison still requires the existing accounting/admission guards; this artifact grants no execution or spending authority.
