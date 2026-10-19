"""Seeded implementation-repair contracts and independent trusted oracles."""
from itertools import combinations

FAMILIES = ("plan", "cover", "merge", "replay")


def reference(family, args):
    if family == "plan":
        graph, changed = args
        affected = set(changed)
        while True:
            expanded = affected | {name for name, deps in graph.items() if affected.intersection(deps)}
            if expanded == affected:
                break
            affected = expanded
        result = []
        while affected:
            ready = min(name for name in affected if not affected.intersection(graph[name]))
            result.append(ready)
            affected.remove(ready)
        return result
    if family == "cover":
        required, suites = args
        candidates = []
        for count in range(len(suites) + 1):
            for choice in combinations(sorted(suites), count):
                covered = {target for name in choice for target in suites[name]["targets"]}
                if set(required) <= covered:
                    candidates.append((sum(suites[name]["cost"] for name in choice), len(choice), choice))
        if not candidates:
            return {"tests": [], "cost": -1}
        cost, _, choice = min(candidates)
        return {"tests": list(choice), "cost": cost}
    if family == "merge":
        intervals, touching = args
        rejected = [i for i, (a, b) in enumerate(intervals) if a >= b]
        result = []
        for a, b in sorted(pair for pair in intervals if pair[0] < pair[1]):
            if result and (a < result[-1][1] or touching and a == result[-1][1]):
                result[-1][1] = max(b, result[-1][1])
            else:
                result.append([a, b])
        return {"intervals": result, "rejected": rejected}
    if family == "replay":
        active, seen, rejected = {}, set(), []
        for event in args[0]:
            identifier = event["id"]
            if identifier in seen:
                continue
            seen.add(identifier)
            if event["kind"] == "add":
                active[identifier] = event["value"]
            elif event["kind"] == "undo" and event["target"] in active:
                del active[event["target"]]
            else:
                rejected.append(identifier)
        return {"total": sum(active.values()), "active": sorted(active), "rejected": sorted(rejected)}
    raise ValueError("unknown hard family")


SPECS = {
    "plan": ("build_plan", "Given an acyclic module->dependency dictionary and changed module names, rebuild changed modules plus all transitive consumers. Return a topological order of the affected modules, always choosing the lexicographically smallest currently ready module. Unaffected dependencies are already built. Every name exists in the graph. Do not mutate inputs.", '''def build_plan(graph, changed):
    affected = list(changed)
    growing = True
    while growing:
        growing = False
        for name in graph:
            for dependency in graph[name]:
                if dependency in affected and name not in affected:
                    affected.append(name)
                    growing = True
    result = []
    while len(result) < len(affected):
        ready = []
        for name in affected:
            if name not in result:
                blocked = False
                for dependency in graph[name]:
                    if dependency in affected and dependency not in result:
                        blocked = True
                if not blocked:
                    ready.append(name)
        result.append(min(ready))
    return result
'''),
    "cover": ("select_tests", "Given a list of required target strings and a dictionary of test suites {name:{targets:[...],cost:positive_integer}}, select suites covering every required target. Minimize total cost, then number of suites, then lexicographic sorted suite-name list. Return {tests:sorted_names,cost:total}. Empty requirements need no suites/cost 0. If impossible return {tests:[],cost:-1}. There are at most 7 suites. Do not mutate inputs.", '''def select_tests(required, suites):
    names = sorted(suites)
    best = None
    for mask in range(2 ** len(names)):
        chosen = []
        covered = []
        cost = 0
        for i in range(len(names)):
            if mask // (2 ** i) % 2 == 1:
                name = names[i]
                chosen.append(name)
                cost = cost + suites[name]["cost"]
                for target in suites[name]["targets"]:
                    if target not in covered:
                        covered.append(target)
        valid = True
        for target in required:
            if target not in covered:
                valid = False
        score = [cost, len(chosen), chosen]
        if valid and (best is None or score < best):
            best = score
    if best is None:
        return {"tests": [], "cost": -1}
    return {"tests": best[2], "cost": best[0]}
'''),
    "merge": ("merge_ranges", "Given unsorted half-open integer interval pairs and merge_touching boolean, return {intervals:sorted_merged_pairs,rejected:original_indices_of_empty_or_reversed_pairs}. Reject pairs with lo>=hi. Merge overlaps; touching intervals merge ONLY when merge_touching is true. Nested/duplicate intervals must not shorten an existing interval. Never mutate any input, including nested pairs.", '''def merge_ranges(intervals, merge_touching):
    rejected = []
    valid = []
    for i in range(len(intervals)):
        lo, hi = intervals[i]
        if lo >= hi:
            rejected.append(i)
        else:
            valid.append([lo, hi])
    result = []
    for pair in sorted(valid):
        if result and (pair[0] < result[-1][1] or merge_touching and pair[0] == result[-1][1]):
            result[-1][1] = max(result[-1][1], pair[1])
        else:
            result.append(pair)
    return {"intervals": result, "rejected": rejected}
'''),
    "replay": ("replay_events", "Replay events in order with first-seen-ID idempotency, even when the first event with that ID was rejected. An add activates its ID with integer value. An undo removes its target ONLY if that target is an earlier still-active add. Unknown kinds, missing/inactive/future targets are rejected. Duplicates are silently ignored, not rejected. Return {total:sum_active_values,active:sorted_active_add_IDs,rejected:sorted_rejected_event_IDs}. Add events have value; undo events have target; unknown kinds have neither. Do not mutate inputs.", '''def replay_events(events):
    seen = []
    active = {}
    rejected = []
    for event in events:
        identifier = event["id"]
        if identifier not in seen:
            seen.append(identifier)
            if event["kind"] == "add":
                active[identifier] = event["value"]
            elif event["kind"] == "undo" and event["target"] in active:
                active.pop(event["target"])
            else:
                rejected.append(identifier)
    return {"total": sum(active.values()), "active": sorted(active), "rejected": sorted(rejected)}
'''),
}


def initial(family, source, difficulty):
    if family == "plan":
        return source.replace("growing = True\n    while", "growing = False\n    while") if difficulty == 1 else "def build_plan(graph, changed):\n    return sorted(changed)\n"
    if family == "cover":
        return source.replace("score = [cost, len(chosen), chosen]", "score = [len(chosen), cost, chosen]").replace('"cost": best[0]', '"cost": best[1]') if difficulty == 1 else 'def select_tests(required, suites):\n    return {"tests": sorted(suites), "cost": 0}\n'
    if family == "merge":
        source = source.replace("max(result[-1][1], pair[1])", "pair[1]")
        return source.replace("merge_touching and pair[0] == result[-1][1]", "pair[0] == result[-1][1]") if difficulty == 2 else source
    if family == "replay":
        source = source.replace('active.pop(event["target"])', 'pass')
        return source.replace('if identifier not in seen:', 'if True:') if difficulty == 2 else source
    raise ValueError("unknown hard family")


def inputs(family, rng, count, difficulty):
    for i in range(count):
        if family == "plan":
            names = ["module_" + str(n) for n in rng.sample(range(80), 5 + 3 * difficulty)]
            graph = {name: [other for other in names[:j] if rng.random() < .35] for j, name in enumerate(names)}
            # Guaranteed consumer chain makes a broken changed-only implementation observable.
            graph[names[1]] = [names[0]]
            changed = [] if i % 11 == 0 else rng.sample(names, 1 + i % 3)
            if i % 3 == 1:
                changed = [names[0]]
            yield [graph, changed]
        elif family == "cover":
            targets = ["target_" + str(n) for n in rng.sample(range(40), 5)]
            names = ["suite_" + str(n) for n in rng.sample(range(80), 3 + 2 * difficulty)]
            suites = {name: {"targets": [t for t in targets if rng.random() < .5], "cost": rng.randint(1, 8)} for name in names}
            required = [] if i % 11 == 0 else rng.sample(targets, 1 + i % 5)
            if i % 7 == 0 and required:
                required.append("missing_" + str(rng.randint(80, 200)))
            yield [required, suites]
        elif family == "merge":
            origin = rng.randint(-40, 40)
            pairs = [[origin, origin + 12], [origin + 1, origin + 4], [origin + 12, origin + 15]]
            pairs += [[rng.randint(-50, 50), rng.randint(-50, 50)] for _ in range(2 + 3 * difficulty)]
            rng.shuffle(pairs)
            yield [pairs, bool(i % 2)]
        elif family == "replay":
            names = ["event_" + str(n) for n in rng.sample(range(1000), 8 + 4 * difficulty)]
            events = [{"id": names[0], "kind": "undo", "target": names[1]},
                      {"id": names[1], "kind": "add", "value": rng.randint(1, 30)},
                      {"id": names[2], "kind": "undo", "target": names[1]},
                      {"id": names[3], "kind": "undo", "target": names[1]}]
            for name in names[4:]:
                kind = rng.choice(["add", "add", "undo", "unknown"])
                event = {"id": name, "kind": kind}
                if kind == "add":
                    event["value"] = rng.randint(-30, 30)
                elif kind == "undo":
                    event["target"] = rng.choice(names)
                events.append(event)
            events.insert(5, {"id": names[0], "kind": "add", "value": 100})
            events.append({"id": names[1], "kind": "add", "value": 99})
            yield [events]
        else:
            raise ValueError("unknown hard family")
