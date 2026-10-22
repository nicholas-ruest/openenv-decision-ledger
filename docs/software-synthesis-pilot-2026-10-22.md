# Missing-component software curriculum

This is a candidate training curriculum, not a trained model or a submission.
The completed Arena result remains2/40, software0/5; retained leaderboard3/40.

## Change that can affect learning

`software_repair-release-d4` asks the model to implement the missing
`build_plan` component: affected-module propagation, affected-only cycles,
downstream blocking, stable topological order and unknown names. The supplied
consumer still performs exact budgeted test-suite selection. Its placeholder
returns the proper dictionary shape, so initial failures are semantic wrong
answers, rather than syntax errors or artificial resource/interpreter traps.

The direct-code application shows all code, the complete contract and examples
before the model responds, then accepts one complete Python module. The d3
control already supplies the graph algorithm and instead has local release
selection defects. This is a curriculum-difficulty comparison, not an isolated
interface or model-improvement estimate.

D4 deliberately uses d3's exact case stream at a shared seed. Public examples,
hidden inputs/labels, full reference, independent oracle and interpreter remain
identical. Only initial code and its explicit component-implementation
instruction change. The existing baseline-normalized reward formula is reused;
the d4 baseline is its own missing-component source. Unit controls require an
executable incomplete repair to score strictly between unchanged and full.
The default eight-task export remains unchanged; d4 is not adopted into it.

## Predeclared measurement

| Property | Synthesis candidate | Capacity control |
| --- | --- | --- |
| Profile |direct_synthesis|direct_capacity_control|
| Task |release-d4|release-d3|
| Screen seeds |1113000,1113100|same|
| Fresh confirmation seeds |1114000,1114100|same|
| Samples per prompt |4|4|
| Interface |one-response direct code|same|
| Max generation / episode units / context |8192 /12288 /24576|same|
| Provider call / stage wall bound |360s /1200s|same|
| Model, route, thinking, temperature |Qwen/Qwen3.8-27B:deepinfra, requested on,0.7|same|

The360-second wait responds to six provider timeouts in the previous180-second
direct screen (two valid full repairs, no valid partial/wrong repairs). It
changes neither per-call token reservation nor phase dollar ceiling. The
whole worker still has its existing1200-second hard deadline. All old profiles
retain180-second waits; no provider/model/provenance substitution is allowed.
The old archives remain independent and cannot be merged into the new cohort.

Each profile has eight independent calls but only TWO unique prompts. Keep
valid semantic full/partial/wrong outcomes separate from format, interpreter,
provider, truncation, usage and budget failures. The existing gate must find
productive signal in BOTH candidate prompt groups before disjoint candidate
confirmation. Control-arm variation cannot qualify d4. A clean-solve increase
or constructed-program controls alone cannot establish learning or promotion.

Arena's actual trainer launches five fresh sandbox episodes per selected task
and uses the first four valid rewards. Our repeated-seed proxy screen is a
different, stricter diagnostic of within-prompt variation. It is not a replay
of Arena sampling, not an attested chat/thinking wrapper, and not evidence of
private software transfer. A later fresh-instance study must be labelled as
across-instance variation, never reclassified as repeated-prompt evidence.

Execution is bounded by the existing privately reconciled inference ledger.
No new credit purchase, GPU rental, weight download, paid target-training job,
HF permission change or Arena POST is performed by this code. Another Arena
request needs the human's explicit review and approval.
