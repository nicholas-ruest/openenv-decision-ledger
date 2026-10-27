# Transactional software-repair training candidate

The previous Arena run evaluated2/40, software0/5. No ranking gain is claimed.
The release-family proxy became saturated: seven of eight live repairs were
fully correct; the eighth used standard tuple-key assignment that our
interpreter rejected. A separate corrected-interpreter replay passes30/30
cases for that code. It is an offline replay, not another live solve, a changed
historical result or model improvement. All old archives remain frozen.

The tuple-key fix makes dictionary assignment consistent with dictionary
literals, comprehensions, lookup/get/pop and augmented assignment. List tuple
indices and non-JSON output remain rejected; source, value and execution limits
are unchanged. Candidate text is still interpreted, never host-executed.

## Original software problem and semantic reward

The new family repairs a versioned key/value command processor: first-seen
idempotency including rejected IDs, atomic multi-operation rollback, sequential
revision checks, deletion tombstones, read-only assertions, empty transactions
and deterministic audit records. The supplied implementation has two(d1) or
four(d2) seeded semantic defects. Six independently instantiated witness cases
exercise the defect catalog. Hidden cases combine fresh witnesses and varied
command sequences, generated independently from public examples. An independent
functional oracle checks the supplied imperative reference implementation.

Reward is substantive correctness, not formatting or fewer actions. Let B be
the original module's count of exactly correct result fields over the30 hidden
cases, C the candidate's count, and T=180 fields (six meaningful fields per
case). Unchanged/cosmetic/non-improving code gets0. A complete exact result on
all30 cases earns1. Otherwise reward is max(0,min(.95,(C-B)/(T-B))). Execution
errors earn no field credit for that case. Values, versions, accepted IDs,
rejected IDs, duplicate count and the entire commit audit each require exact
typed equality. A complete correct shape alone earns no credit, and extra
fields cannot obtain full reward. Older tasks keep their existing reward.

## Frozen experiment, no model training yet

Primary profile `kv_components`: kv-d2, seeds1150000/1150100, four independent
samples per prompt. Easier control `kv_easy_control`: kv-d1 on the same case
streams and seeds. Confirmation uses fresh1151000/1151100. These are only two
unique prompts per arm. Both arms use direct code, Qwen/Qwen3.8-27B:deepinfra,
thinking requested on, temperature.7, JSON object mode,8192 maximum generated
tokens per call,12288 episode units,24576 context units,360s per-request and
1200s whole-worker bounds, with no retries. Source and provider quotes freeze
before admission. Existing privately reconciled append-only spending limits
apply; no purchase is permitted.

Report full, partial and wrong semantic results separately from format,
unsupported-code, provider, truncation and budget failures. Candidate signal
requires at least three valid samples with a full/nonfull mixture in BOTH
primary prompt groups, followed by the same gate on disjoint fresh prompts.
Easy-control variation cannot qualify the primary task. This is a learning
opportunity screen, not evidence of a trained-model improvement. It does not
reproduce Arena's five-fresh-instance/first-four-valid selection or attest its
checkpoint/thinking/chat wrapper.

The new128/32/64 public-fixture splits use1160000+/1170000+/1180000+ and do not
reuse probe/confirmation seeds or the independent1190000+ preparation seeds.
`scripts/export-direct-pilot.py` prepares a source-allowlisted, immutable-image
review bundle and runs oracle/baseline controls. It performs no upload, token
lookup, inference, purchase or submission. Matching public dataset publication,
actual container qualification and explicit approval of the final exact Arena
request remain required. The historical eight-task export is unchanged.
