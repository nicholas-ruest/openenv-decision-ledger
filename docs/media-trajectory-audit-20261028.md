# Media raw trajectory audit, 2026-10-28

This read-only auditor prepares trustworthy future media calibration. It does not call a model, start training, change the environment, or submit to Arena. Software v12 and media v13 remain unchanged and unapproved. No new performance or ranking improvement is claimed.

## What is checked

`research/media-trajectory-audit-20261028/trajectory_audit.py` accepts the unchanged native-derived media protocol and actual frozen schema. Each episode must bind to its planned phase/task/seed/sample, initial request, reset transport and visible workspace. Every attempted call requires its own reservation, request-history hash and unique call identity; returned replies also require response identity and bounded recorded token usage. Request history includes each exact raw assistant reply and the complete native observation transport. No retries are allowed.

Strict action parsing rejects markdown/schema-copying, duplicate JSON keys, unknown fields and nonfinite values. A trusted replay callback receives only validated actions and must reproduce the fresh input workspace/reset and every successfully executed action's observation/reward. The auditor itself never executes model shell text. The native adapter runs in the pinned image over real WebSockets.

The classes are `full`, `wrong`, `format`, `provider`, `truncation`, `execution` and `budget`. Valid semantic rewards are binary. A reward-zero terminal observation's `success:false` is a valid wrong answer, not automatically an infrastructure failure. An ordinary nonterminal shell exit error may be recovered from; an explicit tool timeout or unscored native exception stays separate from wrong. A non-evaluate action that reaches the native 32-action auto-grade is classified as an action-budget stop, retaining its observed terminal reward only as a secondary field. Explicit evaluate on action32 can be valid.

Complete phase assessment requires all 16 independent attempts, rejects duplicate call/response/reservation identities, and reports both the full-attempt solve fraction and conditional fraction among valid completions. Failures never substitute for reward-zero examples when detecting productive groups. Confirmation requires disjoint native cases/workspaces and observed identities. Only the four sampled task/family cells can receive a provisional signal assessment. Initial instruction prefixes may repeat across cases; the existing protocol reports that limitation explicitly.

Unused reservations are listed separately without refunding them. This auditor does not admit expenditure or replace the existing billing/receipt checks. The media plan remains `budget_admitted:false`; no model phase has been admitted or executed.

## Validation

26 local unit tests passed. They cover wrong versus failure distinctions, complete-phase denominators, reused/missing evidence, usage bounds, protocol/schema changes, native replay mismatches, recovery, action32, truncation and provider failures.

The accompanying CI workflow pulls the already qualified immutable media image anonymously. It runs 11 **scripted oracle** trajectories and fresh native TCP replays, covering four sampled cells' full/wrong outcomes plus recovered-command and action32 boundary cases. Provider response IDs, usage and zero-value reservation records in these controls are explicitly synthetic; only reset/workspace/action observations are actual native evidence. Native execution/CI results must be read from the workflow before claiming they passed.

The root-side trusted test adapter identifies the newly created UID workspace and hashes its files without using an episode action. This avoids consuming inspection steps and accidentally testing action30 as action32. It verifies the image's tini entrypoint and imports its native task generator from `/app/qe_arena`. It never sends a request to a provider.

## Limits

Hashes and replay do not cryptographically authenticate provider responses, attest reservation/dispatch chronology or prove the historical shell command executed remotely. Recorded failures are not rerun blindly: native replay checks only the completed action prefix, and unscored exception attribution relies on the external trusted adapter. A future paid coordinator still needs bounded process supervision, durable save-before-next-call, fresh private billing reconciliation, whole-phase admission, provider fingerprints and actual provider result capture.

The unit tests and scripted trajectories establish auditor behavior, not model competence, learning, software/media transfer, a paired treatment effect, or leaderboard improvement. The current requests/images and all paid-execution gates remain frozen.

Upstream environment: [Profa-QE MIT source](https://github.com/proffesor-for-testing/openenv-qe-arena/tree/958198e55299eb18ad812f438a6b2ca6abaa7f5c). Existing [native media protocol](media-matched-protocol-20261027.md) and [qualified media request](../config/media-v13-review-20261027.json).
