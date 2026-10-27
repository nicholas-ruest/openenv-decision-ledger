# Second-category selection: media — 2026-10-27

Media is a **provisional target for a first additional domain point**, not a proven easiest domain or guaranteed ranking improvement. Software and frozen v12 remain intact.

## Public evidence

Profa-QE's public [v7 result table](https://github.com/proffesor-for-testing/openenv-qe-arena/blob/958198e55299eb18ad812f438a6b2ca6abaa7f5c/submission/result-v7r5.md) records media solved in4/7 draws: four of six original-account draws and zero in the independent redraw. Every positive media result is one task. Science/math were trained but not solved in those draws. This is suggestive observational evidence, not an isolated causal media-curriculum comparison. Account/domain maxima can combine different runs; a total is not a single trained policy's score.

This is **Dragan Spiridonov / Profa-QE's MIT-licensed recipe**, not a claimed Reuven Cohen invention. We will credit the actual source rather than label another swarm's results as our own or imply a confirmed Darwin mutation.

## Reproduction completed

Pinned source: `proffesor-for-testing/openenv-qe-arena@958198e55299eb18ad812f438a6b2ca6abaa7f5c`.
MIT copyright2026 Dragan Spiridonov. Retain LICENSE and third-party notices if adapting code.

Ran upstream `tests/test_skills_media.py`: **15 tests passed**. These test drop-frame arithmetic, strict accepted formats and rejection of near misses across timecode/catalogue/assets. They are verifier/oracle tests, not model solves or held-out improvement. Subtitle and complete terminal/container security tests have not yet been reproduced.

Public v7's media cells:
- `qe_skill-media-d1`: timecode, catalogue, assets.
- `qe_skill-media-d2`: subtitles, timecode, catalogue, assets.
- v7 also trained five science/math cells. Removing them produces a changed recipe, not an exact replication.
- The current source also has media-d3, but v7 did not submit it. Do not silently copy v8's task pool into a v7 replication.

Public v7 terminal interface uses exec/write_file/evaluate with4096 completion tokens,8192 context tokens and32 tool calls. Our software direct-code interface differs. A combined image requires deliberate schema/interface integration and fresh validation, not concatenating incompatible task lists.

## Next concrete work

1. Reproduce subtitle and terminal controls in an isolated checkout; inspect sandbox/dependencies before executing untrusted candidates.
2. Prepare a separate media-only adaptation with source/license attribution. Preserve original v7 task pools/budgets as a reference; treat media-only weighting as an untested change.
3. Test meaningful wrong/partial/reference outputs, rejection behavior and realistic observation sizes. Avoid arbitrary difficulty or reward changes.
4. Independently freeze any future matched model calibration with fresh seeds/settings and existing budget admission. No additional paid calls are currently launched.
5. Build/publish/validate any actual proposed image before showing the exact request for approval. Never submit automatically or replace HF data based on this research note.

No media model training, Arena submission, ranking improvement or promotion is claimed here.
