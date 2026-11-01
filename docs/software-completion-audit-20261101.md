# Recorded training-completion metrics, 2026-11-01

The preserved public v11 logs contain a strong clipping signal whose meaning must remain separate from provider finish reasons and semantic grading. Across all 148 optimizer updates, `completions/clipped_ratio` is 1 in 134 updates, 0.75 in 11 and 0.5 in 3. The mean of the per-update ratios is 0.971284; this is **not an attested fraction of individual rollouts**, because the actual per-update sample denominator has not been recovered.

| Recorded numeric task ID | Updates | Updates with clipped ratio 1 | Those also reporting positive reward | Those also reporting reward 1 | Recorded completion length range |
|---|---:|---:|---:|---:|---:|
| 1 | 50 | 39 | 29 | 0 | 525–3398 |
| 2 | 49 | 49 | 49 | 10 | 528–1032 |
| 3 | 49 | 46 | 43 | 0 | 1009–4089 |

All 134 updates with clipped ratio 1 also report zero in all three terminated-length fields. Ten nevertheless report reward 1. Excluding the two updates with nonzero retry counts leaves 146 updates, including 132 with clipped ratio 1 and all ten of those reward-1 updates. These are logged **training rewards**, not ten independently verified complete repairs or held-out solves.

This coexistence prevents using the clipping metric alone as a semantic-failure label. The observed completion lengths also do not identify which configured token limit, serialization rule or EOS handling produced that metric. Actual run-bound trainer revision, tokenizer/termination semantics and original provider finish reasons are still unavailable. The three numeric IDs remain unnamed: no family map is inferred from order, count, reward shape or a different public trainer revision.

The analysis uses the complete public log snapshot read on 2026-10-31 from the [v11 Trackio run](https://openenvarena-training.hf.space/?project=GlobalBusinessAdvisors&runs=a3274296c46341a847407f97). Its saved response file SHA256 is `a832cc88d313b14be5c3567afe8fc81a4c0775b10936536966fbcccd97be0b66`. The selected numeric fixture retains all 148 original ordered steps and thirteen recorded fields. Every selected field and the complete analysis were cross-checked against the full saved response. No prompts, completions, alert bodies, private logs or credentials are published. [Machine-readable result](software-completion-audit-20261101.json).

Three tests passed, including refusal of missing/nonfinite fields, duplicate/reordered steps, incomplete records and inconsistent length summaries. Reproduce from the repository:

```sh
python -B research/software-completion-audit-20261101/analyze.py \
  --logs research/software-completion-audit-20261101/numeric-records.json \
  --output /fresh/path/completion-audit.json
python -B -m unittest discover -s research/software-completion-audit-20261101 -v
```

The current private comparison already uses actual response finish reasons and independently replayed Native outcomes. Keep those classifications unchanged; this historical metric audit neither explains nor repairs the closed helper screen's eight directly observed truncated revisions. No new model calls, cases, training, allocation change or performance gain occurred. No ruOS access occurred overnight. The compact advice candidate remains sealed pending a private source/case audit and fresh complete financial admission; frozen v12 remains untouched.
