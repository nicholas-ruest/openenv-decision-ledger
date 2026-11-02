# Limits of four-draw screens — November 1, 2026

This is an offline calculation from the preserved public outcome table, not a new model experiment. The completed entry-order study remains closed: baseline 4/4 full, treatment 3/4 full, difference −0.25. No confirmation or redraw is permitted.

Under a conditional exchangeable-label Fisher calculation, the observed result has one-sided treatment-better p=1 and two-sided p=1. With four draws per arm, the only positive full-count table with one-sided p≤0.05 is treatment 4/4 versus control 0/4 (p=1/70). For example, treatment 4/4 versus control 1/4 gives p=1/14. These calculations assume independent draws on the fixed prompt; provider correlations can violate that assumption. They do not estimate variation across software tasks.

A separate illustration examines only a reduced rule: treatment has strictly more full solves than control on each of two independent four-draw cases. At equal independent Bernoulli solve probabilities of 0.5, a strict win occurs with probability 93/256 on one case; two wins occur with probability 0.1319733. This is **not the actual protocol gate** and does not estimate its false-positive rate. Additional semantic, infrastructure, exposure and confirmation requirements are not modeled here.

Under the same reduced illustration, a real change from 0.75 to 0.90 full-solve probability produces two strict wins only about 27.8% of the time. Small screens can therefore miss real effects as well as show noisy positive differences. These are assumed probabilities, not estimated model capabilities or measured power of the actual gate.

Practical limit: retain the frozen matched screen and disjoint confirmation as small screening evidence. A positive count difference alone cannot support a confident population-level software-improvement claim. Report all assigned outcomes and uncertainty, and require Arena held-out evidence for leaderboard claims. This analysis changes no selection threshold, resource limit, allocation, case inventory, frozen request or closed-study decision. It does not authorize larger experiments.

Reproduce with `python -B research/software-small-screen-uncertainty-20261101/analyze.py`. The script validates its conditional formula against independent enumeration of labelled allocations for all 25 possible full-count tables, uses exact rational arithmetic, and binds the public result bytes in its output. It reads no private artifacts and makes no network or model calls. No real MetaHarness execution is claimed for this mathematical analysis.
