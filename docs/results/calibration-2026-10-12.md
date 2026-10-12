# Calibration results — October 12, 2026

This report describes proxy calibration of an untrained hosted Qwen/Qwen3.8-27B through Hugging Face's DeepInfra route. It is not a training result or an Arena leaderboard score.

| Difficulty-1 condition | Full solves | Recorded episodes | Provider/interface failures |
|---|---:|---:|---:|
| Thinking requested on | 29 | 32 | 0 |
| Thinking requested off | 1 | 32 | 19 |

Both conditions use the same 32 family/seed cases, seed base 830000. Full solves require reward 1; partial rewards are excluded. Twenty-eight cases were solved only in the thinking-on condition, and none only in the thinking-off condition. The 19 off-condition failures confound a clean reasoning-mode comparison; do not interpret this as an isolated causal effect or a trained-model gain.

The ruOS desktop restarted mid-experiment. Completed records were preserved; incomplete families were replayed, with duplicate family/seed IDs removed from the summary. Source-file hashes and exact counts are in [the JSON report](calibration-2026-10-12.json). Private trajectories and credentials are excluded.

The earlier difficulty-2 thinking-off baseline recorded 1 full solve and 27 partial results across 64 episodes. Its Darwin search found no improvement; confirmation was skipped and no candidate was promoted. The thinking-on Darwin run was still active at the snapshot; 38 full solves were recorded across 52 raw episode records, which include restart/replay records and are not a final independent evaluation set.

The local v2 candidate uses explicit JSON action examples, JSON-object provider output, a pinned DeepInfra route, and Ruv's upstream substantive-component rewards. Empty-answer controls earn zero; partial reward is capped at 0.8. The local validation suite passed 146 tests and 802 subtests. These implementation changes are locally committed and are not included in this report-only PR; the published v1 image and submission draft retain the earlier binary reward.

Provider checkpoint identity and the effect of requested thinking settings are not independently attested. No model weights have been trained, no private Arena evaluation has occurred, and no submission has been sent. Fresh-seed confirmation and the Flywheel gate remain required before promotion.

Upstream reference: [Ruv's public calibration evidence](https://gist.github.com/ruvnet/00fb40aeabb35a893f140597e2695c1d).
