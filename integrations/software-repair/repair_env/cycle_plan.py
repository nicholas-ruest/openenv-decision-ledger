"""Cycle-aware incremental build repair: independent oracle and bounded fixture."""

INSTRUCTIONS = """Repair build_plan(graph, changed). graph maps module names to dependency lists; every dependency exists, but cycles/self-loops are allowed. changed may contain duplicates and unknown names. Return a dictionary with four keys. unknown is the sorted unique unknown changed names. Affected modules are known changed modules and all their transitive consumers. Detect strongly connected components in the graph INDUCED BY AFFECTED MODULES ONLY. cycles is the lexicographically sorted list of sorted cyclic components (size>1, or a singleton with a self-loop). blocked is the sorted union of those components and all their affected transitive consumers. order builds the remaining affected modules, topologically, always choosing the lexicographically smallest currently ready module. Dependencies outside the affected set are already built and do not block, even if cyclic elsewhere. Empty/unknown-only changes yield empty order/blocked/cycles. Do not mutate inputs. At most8 modules. Use only the documented bounded Python subset; no imports, nested functions or nonlocal statements."""

INITIAL = '''def build_plan(graph, changed):
    return {"order": [], "blocked": [], "cycles": [], "unknown": []}
'''

REFERENCE = '''def build_plan(graph, changed):
    unknown = sorted(set([name for name in changed if name not in graph]))
    affected = sorted(set([name for name in changed if name in graph]))
    growing = True
    while growing:
        growing = False
        for name in graph:
            if name not in affected and any([dep in affected for dep in graph[name]]):
                affected.append(name)
                growing = True
    affected = sorted(affected)
    reach = {name: [dep for dep in graph[name] if dep in affected] for name in affected}
    for pivot in affected:
        for name in affected:
            if pivot in reach[name]:
                for target in reach[pivot]:
                    if target not in reach[name]:
                        reach[name].append(target)
    assigned = []
    cycles = []
    blocked = []
    for name in affected:
        if name not in assigned:
            component = [other for other in affected if other == name or other in reach[name] and name in reach[other]]
            for other in component:
                assigned.append(other)
            if len(component) > 1 or name in graph[name]:
                cycles.append(sorted(component))
                for other in component:
                    blocked.append(other)
    growing = True
    while growing:
        growing = False
        for name in affected:
            if name not in blocked and any([dep in blocked for dep in graph[name]]):
                blocked.append(name)
                growing = True
    order = []
    pending = [name for name in affected if name not in blocked]
    while len(order) < len(pending):
        ready = [name for name in pending if name not in order and all([dep not in pending or dep in order for dep in graph[name]])]
        order.append(min(ready))
    return {"order": order, "blocked": sorted(blocked), "cycles": sorted(cycles), "unknown": unknown}
'''


def reference(args):
    """Trusted DFS oracle, independent of the candidate fixture's closure algorithm."""
    graph, changed = args
    unknown = sorted(set(changed).difference(graph))
    affected = set(changed).intersection(graph)
    frontier = list(affected)
    while frontier:
        node = frontier.pop()
        for consumer, deps in graph.items():
            if node in deps and consumer not in affected:
                affected.add(consumer)
                frontier.append(consumer)
    def reachable(start):
        seen, stack = set(), [start]
        while stack:
            node = stack.pop()
            for dependency in graph[node]:
                if dependency in affected and dependency not in seen:
                    seen.add(dependency)
                    stack.append(dependency)
        return seen
    reach = {node: reachable(node) for node in affected}
    remaining, cycles = set(affected), []
    while remaining:
        node = min(remaining)
        component = {other for other in remaining if other == node or other in reach[node] and node in reach[other]}
        remaining.difference_update(component)
        if len(component) > 1 or node in graph[node]:
            cycles.append(sorted(component))
    blocked = {node for component in cycles for node in component}
    for node in affected:
        if reach[node].intersection(blocked):
            blocked.add(node)
    pending, order = affected.difference(blocked), []
    while pending:
        node = min(node for node in pending if not pending.intersection(graph[node]))
        pending.remove(node)
        order.append(node)
    return {"order": order, "blocked": sorted(blocked), "cycles": sorted(cycles), "unknown": unknown}


def inputs(rng, count):
    for i in range(count):
        names = ["module_" + str(n) for n in rng.sample(range(200), rng.randint(6, 8))]
        graph = {name: [other for other in names[:j] if rng.random() < .3] for j, name in enumerate(names)}
        mode = i % 6
        changed = [names[0]]
        if mode == 0:
            changed = [] if i % 12 == 0 else rng.sample(names, 2)
        elif mode == 1:
            graph[names[0]] = [names[0]]
            graph[names[1]] = [names[0]]
        elif mode in (2, 3, 4):
            graph[names[0]] = [names[1]]
            graph[names[1]] = [names[0]]
            if mode == 2:
                graph[names[2]] = [names[1]]
            elif mode == 3:
                graph[names[2]] = [names[3], names[0]]
                graph[names[3]] = [names[2]]
            else:
                changed = [names[-1]]
        else:
            changed = [names[0], names[0], "unknown_" + str(rng.randint(300, 500))]
        yield [graph, changed]
