"""Exact small-screen sensitivity, using public closed outcomes only.

No private inputs, model calls, selection/promotion authority or gate changes.
"""
from fractions import Fraction
from itertools import combinations
from math import comb
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]


def fisher(control, treatment, n=4):
    """Conditional exchangeable-label hypergeometric calculation."""
    if any(type(x) is not int for x in (control, treatment, n)) or n < 1 or not (0 <= control <= n and 0 <= treatment <= n):
        raise ValueError('bounded integer full-solve counts required')
    total = control + treatment
    masses = {k: Fraction(comb(n, k) * comb(n, total-k), comb(2*n, total))
              for k in range(max(0, total-n), min(n, total)+1)}
    observed = masses[treatment]
    return sum((p for k,p in masses.items() if k >= treatment), Fraction()), sum((p for p in masses.values() if p <= observed), Fraction())


def positive_difference_probability(control_p, treatment_p, n=4):
    """Illustrative independent Bernoulli draws, not the actual protocol gate."""
    c,t = Fraction(control_p), Fraction(treatment_p)
    if not (0 <= c <= 1 and 0 <= t <= 1):raise ValueError('probabilities required')
    return sum((comb(n,b)*c**b*(1-c)**(n-b) * comb(n,a)*t**a*(1-t)**(n-a)
                for b in range(n+1) for a in range(b+1,n+1)), Fraction())


def validate():
    # Independent labelled-assignment enumeration checks the conditional formula.
    for c in range(5):
        for t in range(5):
            allocations = list(combinations(range(8), c+t))
            counts = [sum(i < 4 for i in positions) for positions in allocations]
            enumerated = Fraction(sum(k >= t for k in counts), len(counts))
            assert fisher(c,t)[0] == enumerated
    assert fisher(4,3) == (Fraction(1), Fraction(1))
    assert fisher(0,4)[0] == Fraction(1,70)
    assert positive_difference_probability('1/2','1/2') == Fraction(93,256)


def analyze():
    path = ROOT/'docs/software-entry-order-screen-results-20261101.json'
    raw = path.read_bytes();result = json.loads(raw)
    if (result['kind'] != 'software_entry_order_review_screen_results' or
        result['assigned'] != 8 or not result['all_original_assignments_independently_verified'] or
        result['unknown_usage_calls'] != 0 or result['known_replies'] != 16 or
        [g['assigned'] for g in result['groups']] != [4,4] or result['selection_passed']):
        raise ValueError('original complete closed failed screen only')
    observed_c,observed_t = [g['full'] for g in result['groups']]
    one,two = fisher(observed_c,observed_t)
    strict = [(c,t,str(fisher(c,t)[0])) for c in range(5) for t in range(c+1,5) if fisher(c,t)[0] <= Fraction(1,20)]
    illustrative = []
    for c,t in [('1/2','1/2'),('3/4','9/10'),('3/4','1')]:
        p = positive_difference_probability(c,t)
        illustrative.append(dict(control_probability=c,treatment_probability=t,
            strict_full_count_win_probability=float(p),two_independent_cases_both_win_probability=float(p*p)))
    return dict(kind='closed_small_screen_uncertainty_analysis',public_results_sha256=hashlib.sha256(raw).hexdigest(),
        observed_control_full=observed_c,observed_treatment_full=observed_t,
        observed_rate_difference=(observed_t-observed_c)/4,
        conditional_one_sided_p=float(one),conditional_two_sided_p=float(two),
        four_per_arm_positive_outcomes_with_one_sided_p_at_most_point05=strict,
        illustrative_strict_win_only=illustrative,
        actual_selection_rule_unchanged=True,actual_protocol_false_positive_rate_estimated=False,
        new_cases=0,new_model_calls=0,model_improvement=False,leaderboard_gain=False,
        assumptions=['Fisher calculation assumes exchangeable labels and independent draws conditional on this one prompt; provider correlations can violate this.',
            'Illustrations use only the reduced strict full-count win rule and independent cases. They do not implement or estimate the actual MetaHarness screen/confirmation gate.',
            'Repeated draws on one case are not independent task instances. No task-population interval or software transfer claim follows.',
            'No thresholds, resources, allocations, frozen requests or closed-study decisions are changed.'])


if __name__ == '__main__':
    validate()
    print(json.dumps(analyze(),indent=2))
