"""Release-contract witnesses with independently varied public/hidden names.

Each of the four existing semantic faults has its own isolated example. The
contract, exhaustive oracle, source mutations and interpreter limits are shared
with release-d1. These cases add feedback coverage rather than new failure modes.
"""


def inputs(rng, count):
    for index in range(count):
        a, b, x, y, z, w = [f"module_{n}" for n in rng.sample(range(1_000_000), 6)]
        ids = sorted(f"suite_{n}" for n in rng.sample(range(1_000_000), 6))
        graph = {name: [] for name in (a, b, x, y, z, w)}
        changed = [x]
        budget = rng.randint(1, 3)
        suites = {name: {"targets": [], "cost": budget + 100} for name in ids}
        mode = index % 6
        if mode == 0:  # Blocked modules do not require coverage.
            graph[a], graph[b] = [b], [a]
            changed = [a, x]
            suites[ids[0]] = {"targets": [a, b], "cost": 0}
            suites[ids[1]] = {"targets": [x], "cost": 0}
        elif mode == 1:  # Coverage precedes cost, without ties or boundary effects.
            changed = [x, y]
            unit = rng.randint(2, 9)
            budget = 3 * unit
            suites = {name: {"targets": [], "cost": budget + 100} for name in ids}
            suites[ids[0]] = {"targets": [x], "cost": unit}
            suites[ids[1]] = {"targets": [x, y], "cost": 2 * unit}
        elif mode == 2:  # A free suite fits a zero budget, inclusively.
            budget = 0
            suites[ids[0]] = {"targets": [x], "cost": 0}
        elif mode in (3, 4):
            # Exactly two minimum-cardinality covers: [0,3] and [1,2].
            # Cross-pairs each miss a target; reversing the tie key changes
            # the winner. Free suites isolate this from cost-priority faults.
            changed = [x, y, z, w]
            for name, targets in zip(ids, ([x, y], [x, z], [y, w], [z, w])):
                suites[name] = {"targets": targets, "cost": 0}
            if mode == 4:  # Compound boundary, blocked-coverage and tie example.
                graph[a], graph[b] = [b], [a]
                changed.append(a)
                budget = 0
                suites[ids[4]] = {"targets": [a, b], "cost": 0}
        else:  # Unknown changes and no required buildable modules.
            missing = f"missing_{rng.randrange(1_000_000)}"
            changed = [missing, missing]
        rng.shuffle(changed)
        # Vary insertion order independently of the contract's sorted tie rule.
        items = list(suites.items())
        rng.shuffle(items)
        yield [graph, changed, dict(items), budget]
