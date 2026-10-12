# ADR 1: Separate episode runtime, search, and submission
Status: accepted.
Arena's fixed model trains in ephemeral CPU sandboxes. Keep the image self-contained and use OpenEnv at the Arena pin. Virtual task files are episode state; no external persistence is required. Do not introduce a service database.
MetaHarness Darwin/Flywheel remains outside the image. Darwin measures reasoning-driven reward variation, rejects infrastructure-confounded cards, and confirms the selected winner against a baseline on disjoint seeds. A confirmation receipt is evidence, never Nick's submission authorization.
Every Arena POST requires the exact request to be shown to Nick and explicit approval. No timer or auto-submit is installed. Public board updates must exclude credentials and private logs.
Use full-credit terminal rewards to avoid rewarding short categorical guesses. Preserve independent oracle checks, malformed answers, early finish, immutable terminal state, seed determinism and source-bound runtime replay.
Changes to upstream reward semantics require regression tests. Inherited upstream performance artifacts are removed.
