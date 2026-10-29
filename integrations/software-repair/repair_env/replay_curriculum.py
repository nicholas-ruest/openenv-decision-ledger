"""Behavior-isolated replay cases, retaining compound cases and 18 events each."""


def inputs(rng, count):
    for index in range(count):
        names = ["event_" + str(n) for n in rng.sample(range(1000), 32)]
        a, b, c, d, _, future = names[:6]
        value = rng.randint(1, 30)
        negative = -rng.randint(1, 30)
        mode = index % 6
        if mode == 0:  # Effective undo, no duplicate IDs.
            events = [{"id": a, "kind": "add", "value": value},
                      {"id": b, "kind": "add", "value": negative},
                      {"id": c, "kind": "undo", "target": a}]
        elif mode == 1:  # Duplicate adds, no effective undo.
            events = [{"id": a, "kind": "add", "value": value},
                      {"id": a, "kind": "add", "value": value + 1},
                      {"id": b, "kind": "add", "value": negative}]
        elif mode == 2:  # Both faults affect the result.
            events = [{"id": a, "kind": "add", "value": value},
                      {"id": b, "kind": "undo", "target": a},
                      {"id": a, "kind": "add", "value": value + 1},
                      {"id": c, "kind": "add", "value": negative},
                      {"id": b, "kind": "undo", "target": c}]
        elif mode == 3:  # A rejected first-seen ID still suppresses duplicates.
            events = [{"id": a, "kind": "undo", "target": b},
                      {"id": b, "kind": "add", "value": value},
                      {"id": a, "kind": "add", "value": value + 1},
                      {"id": c, "kind": "unknown"},
                      {"id": b, "kind": "add", "value": value + 2}]
        elif mode == 4:  # Effective, repeated-target and future-target undos.
            events = [{"id": a, "kind": "add", "value": value},
                      {"id": b, "kind": "undo", "target": a},
                      {"id": c, "kind": "undo", "target": a},
                      {"id": d, "kind": "undo", "target": future},
                      {"id": future, "kind": "add", "value": negative}]
        else:  # Unknown kinds are first-seen IDs too.
            events = [{"id": a, "kind": "unknown"},
                      {"id": b, "kind": "add", "value": value},
                      {"id": a, "kind": "add", "value": value + 1},
                      {"id": c, "kind": "undo", "target": names[7]},
                      {"id": b, "kind": "add", "value": value + 2}]
        # Match legacy replay-d2's event count. Unique benign adds preserve the
        # behavior being isolated without reducing interpreter/resource limits.
        for name in names[8:8 + 18 - len(events)]:
            events.append({"id": name, "kind": "add", "value": rng.randint(-30, 30)})
        yield [events]
