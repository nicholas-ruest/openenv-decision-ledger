# v11 reported clipping and public actor-interface check, October 31, 2026

The preserved actual v11 trainer logs report completions/clipped_ratio equal to 1.0 on **134 of 148 optimizer updates**. Eleven updates report 0.75 and three report 0.5. These are reported trainer fields, not reconstructed provider finish reasons or a new model evaluation.

The public records were reread on October 31 and matched the preserved audit exactly. Normalized raw-log SHA256: `443f811e9b61b52f77f6b10425d2111941ab8851e22fb15bf6a2608f262b30b9`. The earlier exact-step audit cross-checked all 1,036 values from seven metric series. [Actual public run](https://openenvarena-training.hf.space/?project=GlobalBusinessAdvisors&runs=a3274296c46341a847407f97).

| Recorded numeric task ID | Updates | Updates reporting ratio 1.0 | Updates with positive reported maximum terminated length | Zero-retry updates with reward 1 and std 0 |
| --- | ---: | ---: | ---: | ---: |
| 1 | 50 | 39 | 11 | 0 |
| 2 | 49 | 49 | 0 | 10 |
| 3 | 49 | 46 | 3 | 0 |

Numeric IDs are the actual step/task values. Their task-name mapping remains unattested; no rotation or family attribution is inferred.

Of the 146 updates with zero recorded retries, 132 report clipping ratio 1.0. All ten reward-saturated zero-retry updates also report ratio 1.0. Among 121 zero-retry updates with nonzero reward std and gradient, 109 report ratio 1.0. Thus this reported clipping field can coexist with positive reward, saturated reward, and nonzero recorded variation/gradient. It must not automatically become a provider-failure or unusable-training label.

Reported maximum completion lengths span 596–4,089; the range for numeric group 2 is 596–1,032. These values alone do not attest a fixed production token cap. The mean of per-update reported clipping ratios is 0.9712837838; it is not a token-weighted estimate or an independently counted fraction of all provider responses.

## Interpretation boundary

The exact managed actor/rollout implementation and the semantics generating these metrics remain unavailable in the public relay source. Consequently this report does **not** establish that every reported clipped sample exhausted a generation budget, that reasoning consumed all output, that EOS handling was defective, or that clipping caused software held-out failure. No provider stop reason is manufactured from these trainer metrics. Likewise training rewards and gradients do not establish software transfer.

This is a concrete reason to attest the trainer's stopping and accounting conventions before translating the private revision-only-thinking serving result into a managed training request. It does not authorize changing token scope, teacher settings or the frozen request.

## Public interface check

The public Space metadata was checked at 2026-10-31T09:01:54Z. Arena remains at revision `c3d621f17449212c19f74026d41e498e4d3b148d`; training remains at `362671b590eb2536f86d86bd211b44f7af61bd04`. Their published file inventories are unchanged from the earlier source audits. No newly exposed public actor implementation or documented per-response thinking control was found by this revision check. This does not attest the private cluster's current implementation.

Primary source revisions: [Arena](https://huggingface.co/spaces/openenvarena/arena/tree/c3d621f17449212c19f74026d41e498e4d3b148d), [training](https://huggingface.co/spaces/openenvarena/training/tree/362671b590eb2536f86d86bd211b44f7af61bd04).

## Reproduction

The [numeric aggregate receipt](results/software-v11-reported-clipping-20261031.json) contains only counts and recorded-field summaries. No prompts, completions, alert bodies, private trajectories or financial data are included. Obtain the fixed run's public get_run_summary and get_logs responses with the existing bounded public collector, then run:

```bash
python scripts/analyze-v11-reported-clipping.py --summary get_run_summary.json --logs get_logs.json --output reported-clipping.json
```

The analyzer validates exact run/count binding, unique optimizer steps, finite observed metrics, integer numeric IDs and ratio bounds. It assigns no task names or causal labels.

This analysis used existing logs. No ruOS access, model call, new training, ledger/cap change, submission, HF replacement or leaderboard gain occurred. The already-qualified output-contract screen remains first in queue; its private admission and durable storage requirements are unchanged.
