# Focused direct-code repair experiment

The Oct21 Arena run completed189 updates and evaluated2/40, including0/5 in
software. The retained leaderboard is3/40. No transfer gain is established.
That outcome motivates a new experiment, not a new submission or a claim that
the following interface will improve private evaluation.

## Concrete change

A separate `repair_env.direct_app` presents the broken module, complete
contract, supported-language rules and six public examples in the initial
observation. The sole action is `{"content":"complete repaired module"}`.
It submits once. The existing edit/test application and its default export are
preserved. The same `RepairEnvironment` evaluates the candidate internally:
same original module, hidden cases, reference/oracle, byte/interpreter bounds,
AST-change requirement and baseline-normalized partial reward. There is no
reward for JSON compliance, fewer actions, unchanged code or matching examples
without satisfying hidden cases. No host execution of candidate Python.

The hypothesis is that fewer tool-format and observation-budget failures will
make repair-quality differences measurable. It does not assume the model
learned nothing in the prior run. The Trackio metrics are presently unreadable;
`budget_spent`/`trainer_failure` event ordering does not establish a crash.
Another participant reports the same ordering on completed runs, but that is
not organizer confirmation.

## Frozen proxy comparison

One family: `software_repair-release-d3`, involving affected-module graph
reasoning and budgeted test-suite selection. Both arms use the identical task
objects, initial code and public/hidden inputs for each seed.

| Property | Direct-code arm | Interactive control |
| --- | --- | --- |
| Profile | `direct_release` | `direct_release_control` |
| Screen prompts |1111000,1111100|1111000,1111100|
| Samples per prompt |4|4|
| Total screen rollouts |8|8|
| Maximum actions |1|12|
| Maximum generation per call |8192|8192|
| Episode generation + later observations |12288|12288|
| Context limit |24576|24576|
| Transport/model |streamed Qwen/Qwen3.8-27B:deepinfra|same|
| Thinking/temperature |requested on,0.7|same|
| Retry |none|none|

The interface bundle changes schema, initial observation and permitted action
count together. This experiment cannot isolate which of those changes causes
an observed difference. Eight samples are only TWO unique prompts per arm;
arms share prompt task content intentionally. Provider quote/provenance must
match, and client labels/response IDs must remain independently auditable.

Measure clean full/partial/wrong repairs separately from JSON/schema,
interpreter, provider, truncation and budget failures. Compare actual completion
and observation token usage, action counts and hidden-case diagnostics. All
valid rewards being1 is saturation, not a productive learning signal.

Only a candidate passing the existing semantic gate on BOTH prompt groups may
be considered for confirmation on fresh1112000/1112100, with settings and
source frozen. Higher clean completion alone does not authorize a training mix
promotion. Report a rejected or saturated experiment honestly.

Execution requires the already-authorized, privately reconciled, append-only
inference allocation. CPU controls and image qualification are not model
learning. Proxy thinking/checkpoint/Arena-wrapper equivalence remains
unattested. No new Arena POST, GPU rental, weight download, paid training,
credit purchase or permission change is implemented or authorized here.
