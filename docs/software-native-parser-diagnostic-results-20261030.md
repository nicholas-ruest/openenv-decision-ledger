# Submitted-source parser diagnostics: incomplete screen, October 30, 2026

The screen at source `83d56ec56fef1e0932b7258766f86dda0c1b93a4` was **closed incomplete without retry** after a control request timed out at 360.251 seconds with unknown generation usage.

Eight attempts were assigned (four per arm). Four were recorded: standard review had one partial solve at 0.55 and one provider timeout; diagnostic review had one full solve and one final-response truncation. Four assigned attempts were never called. There were **seven actual calls and six known replies**. The known replies were independently replayed with exact request, identity, usage and Native grade bindings. The missing reply remains unknown; it was not certified as complete and its reservation is retained.

The parser diagnostic was actually delivered in the diagnostic attempt that later truncated. The diagnostic arm's full solve received **no parser diagnostic**, because its first proposal did not trigger that field. Thus the observed full solve does not show that the diagnostic helped.

Both local supervisors closed cleanly and their workers stopped. The remaining frozen chunks were not launched, and reserved confirmation 2990000 was not materialized. No completed-screen selection, improvement, promotion, training gain or leaderboard gain is claimed. Incomplete/unknown-usage groups were not assigned an invented MetaHarness fitness score.

Both arms had identical first prompts, public-field feedback and review advice. Only treatment added submitted-source-only Native parser diagnostics when its proposal was rejected for invalid/unsupported syntax. The interpreter, Native hidden grader, provider sampling and 8,192/24,576 budgets were unchanged. This was a separate study from helper retention and public-example feedback. See [qualification](software-native-parser-diagnostics-20261030.md).

A separate sorting compatibility candidate addresses actual valid-Python rejection. It is not being used to revise these results. No Arena POST, dataset replacement or reviewed v12 change occurred.
