"""Compound release-planning repairs with an independent exhaustive oracle."""

import hashlib
from itertools import combinations
import random

from . import cycle_plan

INSTRUCTIONS = cycle_plan.INSTRUCTIONS.replace(
    "Repair build_plan(graph, changed).", "Repair plan_release(graph, changed, suites, budget)."
) + (
    " Also return affected, tests, test_cost and uncovered. affected is the sorted "
    "union of order and blocked. suites maps test-suite IDs to dictionaries with "
    "targets (module names) and a nonnegative integer cost; there are at most six "
    "suites. Only buildable affected modules (the modules in order) need test "
    "coverage. Covering blocked or unaffected modules gives no benefit and is "
    "allowed. Select suites with total cost <= budget, a nonnegative integer. "
    "Minimize, IN THIS ORDER: number of uncovered required modules, total cost, "
    "number of suites, then the sorted selected suite-ID list lexicographically. "
    "Insufficient budget may leave modules uncovered; return them sorted. "
    "Zero-cost suites and a zero budget are valid. tests is the sorted selected "
    "ID list; test_cost is its exact sum. Do not mutate any inputs."
)

REFERENCE = cycle_plan.REFERENCE + '''
def plan_release(graph, changed, suites, budget):
    base = build_plan(graph, changed)
    required = set(base["order"])
    names = sorted(suites)
    best = None
    best_tests = []
    best_cost = 0
    best_uncovered = sorted(required)
    for mask in range(2 ** len(names)):
        selected = []
        covered = set()
        cost = 0
        for index in range(len(names)):
            if mask & (1 << index):
                name = names[index]
                selected.append(name)
                covered.update(suites[name]["targets"])
                cost += suites[name]["cost"]
        if cost <= budget:
            uncovered = sorted(required.difference(covered))
            key = (len(uncovered), cost, len(selected), selected)
            if best is None or key < best:
                best = key
                best_tests = selected
                best_cost = cost
                best_uncovered = uncovered
    return {"affected": sorted(base["order"] + base["blocked"]),
            "order": base["order"], "blocked": base["blocked"],
            "cycles": base["cycles"], "unknown": base["unknown"],
            "tests": best_tests, "test_cost": best_cost,
            "uncovered": best_uncovered}
'''


def initial(seed):
    material = f"software-release-repair|{seed}|defects".encode()
    rng = random.Random(int.from_bytes(hashlib.sha256(material).digest(), "big"))
    defects = rng.sample(range(4), 3)
    source = REFERENCE
    if 0 in defects:
        source = source.replace('required = set(base["order"])',
                                'required = set(base["order"] + base["blocked"])')
    if 1 in defects:
        source = source.replace("key = (len(uncovered), cost, len(selected), selected)",
                                "key = (cost, len(uncovered), len(selected), selected)")
    if 2 in defects:
        source = source.replace("if cost <= budget:", "if cost < budget:")
    if 3 in defects:
        source = source.replace("len(selected), selected)", "len(selected), selected[::-1])")
    return source


def reference(args):
    """DFS graph oracle plus combinations, independent of fixture bitmasks."""
    graph, changed, suites, budget = args
    base = cycle_plan.reference([graph, changed])
    required = set(base["order"])
    choices = []
    for size in range(len(suites) + 1):
        for selected in combinations(sorted(suites), size):
            cost = sum(suites[name]["cost"] for name in selected)
            if cost > budget:
                continue
            covered = {target for name in selected for target in suites[name]["targets"]}
            uncovered = sorted(required.difference(covered))
            choices.append(((len(uncovered), cost, size, selected), uncovered))
    (_, cost, _, selected), uncovered = min(choices)
    return {**base, "affected": sorted(base["order"] + base["blocked"]),
            "tests": list(selected), "test_cost": cost, "uncovered": uncovered}


def inputs(rng, count):
    for index, (graph, changed) in enumerate(cycle_plan.inputs(rng, count)):
        names = list(graph)
        if index % 6 in (1, 2, 3):
            graph[names[-1]] = []
            changed = changed + [names[-1]]
        identifiers = ["suite_" + str(i) for i in rng.sample(range(100), 6)]
        suites = {
            name: {"targets": rng.sample(names, rng.randint(0, len(names))),
                   "cost": rng.randint(0, 7)} for name in identifiers
        }
        suites[identifiers[0]] = {"targets": names[:], "cost": rng.randint(6, 14)}
        budget = [0, 5, suites[identifiers[0]]["cost"], 10, 3, 7][index % 6]
        if index % 6 == 4:
            required = cycle_plan.reference([graph, changed])["order"]
            for name in identifiers[1:3]:
                suites[name] = {"targets": required[:], "cost": 3}
        yield [graph, changed, suites, budget]
