# Software-only public trial for human review — 2026-10-20

The existing public software-repair candidate is technically ready for an exploratory Arena trial. This is a distinct proposal for source `c95e6fe79e44c9b1514fd59e186a0a70ac424858`, matching the already-public Hugging Face source archive, schema and all 128 exported workspaces. It does not replace or promote the retained `7156868` compact-feedback candidate. That newer candidate's public dataset bundle has not been published. There is no measured evidence that this earlier candidate outperforms the newer candidate.

[Exact POST body](../../config/software-repair-public-trial-20261020.json), SHA256 `acc4b04f87db6c86a0bf8dcc75352dc4b80bf82cabe80526904b5852c07223ad`.

Endpoint: `POST https://openenvarena-arena.hf.space/api/openenv/submissions`. **Do not POST before the human explicitly approves this exact request.** Acceptance automatically starts Arena training.

The body uses submission ID `decision-ledger-software-repair-v3-20261020`, the immutable `b515cb39…` image, and `GlobalBusinessAdvisors/openenv-decision-ledger`. The observed public dataset revision is `063900b75ac26423166a80d11e814092b1d05627`; the API snapshots its head at acceptance rather than accepting a revision in the request. Recheck that head before sending.

Eight train tasks: plan, cover, merge and replay, each at d1/d2. Each has 12 tool calls, 600-second rollout, 8,192 completion tokens and 16,384 context tokens. Actions: list/read/write/test/submit. No patch action is declared for this image.

Fresh no-model verification reproduced all 128 unique public workspaces, obtained zero reward for unchanged code and full reward for reference repairs on all 128 cases, and confirmed exact schema/task-ID correspondence. The public ZIP's Git archive comment pins the source commit above. An anonymous registry read confirmed the submitted manifest digest, linux/amd64 architecture and 207,996,908 compressed layer bytes. The existing [CI](https://github.com/nicholas-ruest/openenv-decision-ledger/actions/runs/39264013027) was rechecked as successful, including the anonymous image replay job.

These are software controls, not model solves or evidence of learning. The task mix remains provisional. Earlier valid proxy completions were full solves, while non-solves included infrastructure/budget failures; productive training signal remains unconfirmed. No top-ten prediction follows from these checks. The purpose of this proposal is to obtain a measured Arena result for the software edit/test curriculum while preserving the newer candidate and all prior evidence.

No submission, paid inference, GPU rental or additional purchase was made during this preparation. The exact-request approval requirement comes from the user's instruction and the Arena AGENTS guide.
