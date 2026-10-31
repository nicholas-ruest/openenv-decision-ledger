# First-proposal retention audit

This is a **posthoc controller counterfactual**, not a model comparison, training run, or admission tool. It diagnoses whether an already generated first proposal that passed every supplied public example was correct before a later final response.

The rule is frozen before evaluating private traces:

1. Require an original, independently replayable live archive with known usage and unchanged source.
2. Require the first response to end normally, parse through the original action parser, and yield an original nonterminal zero-reward review.
3. Retain only when the review explicitly identifies a public-only field check, denies hidden access, and reports positive integer counts with every public example passing.
4. After that decision, submit the original supported empty action through the unchanged Native Trial to grade the retained first proposal. This action is controller-authored, never an observed model response.
5. Keep each study and arm separate. Do not call posthoc counterfactual grades model solves, completed effect estimates, fresh confirmation, or leaderboard improvement.

No provider, credential, spending, reservation, training, submission or dataset API is called. The script writes no output file; it prints aggregate results and evidence digests. Run one protocol per process because the historical study modules share Python import names.

Four focused controls passed using the actual pinned Native task package: strict public-only trigger fields, reference-proposal retention through the original empty action, no hidden finalization for a failing public review, and refusal to recover a truncated response. These are trusted qualification controls, not model samples.

The earlier **retention-advice model study remains failed**; this diagnostic cannot reverse that result. Any future controller candidate needs a newly frozen, admitted model comparison on fresh disjoint cases and unchanged accounting and operating-hour protections.
