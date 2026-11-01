# Initial helper guidance: Native qualification, November 1

The existing October 27 helper-preservation instruction is now connected to the original one-response Native full-module interface in `research/software-preserve-first-action-20261101/preserve_first.py`. Only the initial observation's prompt suffix changes. Source, examples, action schema, task contract and Native grading match across arms. The actual generated module is submitted unchanged; there is no helper restoration, second response, self-check instruction or reference insertion.

This is distinct from the failed post-proposal forced helper-restoration controller. It also does not reopen initial public-example self-tracing: that earlier screen's apparent benefit failed fresh disjoint confirmation (1/4 full repairs in each arm). See the [closed October 29 report](https://github.com/nicholas-ruest/openenv-decision-ledger/blob/0e9b6f1e0008c34e9330c8219873c90ba1865c32/docs/software-selfcheck8-results-20261029.md). The November 1 advice result's earlier next-step pointer was corrected after reviewing that evidence.

Six focused tests passed both locally and on ruOS against actual Native code and the pinned tokenizer. The ruOS run used clean immutable source `f4059008d176213df8ad1b9f9ecdefb93e0a70f1` and completed with verified exit zero. They check the prompt-only difference; unchanged generated code and identical terminal reference grade; separation of valid wrong from execution failure; terminal handling of length/provider/format failures without retry; rejection of new/live inputs; and counting the actual terminal observation within the existing reserve. Reference controls are not sampled model solves. Qualification uses only an already-seen case and performs no provider requests or fresh case generation.

Live screen and confirmation materialization explicitly fail. No financial admission, execution readiness or improvement is claimed. A future comparison still needs a separately frozen counterbalanced schedule, independent raw-call and Native replay evidence, immutable private source/case leases and complete fresh accounting before any paid request. The intended scope is four samples per matched arm on one software prerequisite case per phase, followed only after positive complete-screen selection by unchanged fresh disjoint confirmation. Eight samples are not eight independent procedural cases. Every failure remains in the denominator.

The existing route (`Qwen/Qwen3.8-27B:deepinfra`), temperature 0.7 and JSON mode remain matched. Thinking mode remains provider default and is not independently attested. The proposed one-action protocol retains the existing first-generation ceiling 6000, generation plus all observations 8192, context 24576, terminal observation reserve 96, request 360 seconds, attempt 600 seconds and one whole-phase 1200-second supervisor. These constants do not themselves enforce a live call; no live caller has been supplied by this prototype.

Run qualification with the existing environment and pinned tokenizer:

```bash
HELPER_TEST_TOKENIZER=/path/to/pinned-tokenizer.json python -B -m unittest discover \
  -s research/software-preserve-first-action-20261101 -p 'test_preserve_first.py' -v
```

Frozen v12 and its request, image and dataset remain unchanged and unapproved. This preparation is neither managed training nor leaderboard evidence.
