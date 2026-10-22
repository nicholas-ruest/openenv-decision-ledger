"""Original transactional key/value implementation task and independent oracle."""
import hashlib
import random

INSTRUCTIONS = """Repair replay_store(initial, commands), a transactional versioned key/value API. initial maps string keys to integers. Initial keys have revision0; absent never-written keys also have revision0. Each top-level command has a string id and op. First-seen IDs are consumed EVEN IF REJECTED. A repeated ID is silently ignored and increments ignored; it produces no accepted/rejected/commit entry. Preserve input order in accepted and rejected.
put/delete/check operations have key and expect (null means unconditional, otherwise it must equal that key's CURRENT REVISION, not its value). put has value: write it and increment revision even if the value is unchanged. delete requires a present key: remove its value and increment its revision; KEEP that tombstone revision. check has exists:boolean and value: require existence to equal exists and, when exists is true, exact value equality; check changes neither value nor revision. Unknown operations are rejected.
batch has ops, a list of put/delete/check or unknown operations WITHOUT IDs. Execute them sequentially against tentative values AND revisions. A failed sub-operation rejects the ENTIRE batch and rolls back every tentative value/revision change. A later sub-operation sees earlier tentative writes/revisions. An empty batch succeeds. Unknown top-level operations are rejected. Commands and operations are well-formed for their stated kind.
Return exactly {values:final_present_values, versions:revisions_including_tombstones, accepted:ordered_successful_IDs, rejected:ordered_rejected_IDs, ignored:duplicate_count, commits:ordered_records}. Every accepted top-level command, including checks and empty batches, appends a record {id:its_ID,writes:sorted_unique_keys_written_by_put_or_delete,version_sum:sum_FINAL_revisions_of_those_unique_keys}. Checks never add write keys; multiple writes to one key increment its revision each time but count the key once in that commit. Failed commands append no record. Do not mutate inputs. At most24 top-level commands,4 sub-operations per batch and8 distinct keys. Partial reward requires improving correct semantic result fields over the supplied broken code on independent hidden cases; full reward requires the complete exact result on EVERY hidden case. Correct format, unchanged code and shorter output earn no bonus."""

REFERENCE = '''def apply_one(values, versions, command):
    kind = command["op"]
    if kind not in ["put", "delete", "check"]:
        return False
    key = command["key"]
    current = versions.get(key, 0)
    expected = command["expect"]
    if expected is not None and expected != current:
        return False
    if kind == "put":
        values[key] = command["value"]
        versions[key] = current + 1
        return True
    if kind == "delete":
        if key not in values:
            return False
        values.pop(key)
        versions[key] = current + 1
        return True
    if command["exists"] != (key in values):
        return False
    return not command["exists"] or values[key] == command["value"]

def replay_store(initial, commands):
    values = initial.copy()
    versions = {key: 0 for key in initial}
    seen = []
    accepted = []
    rejected = []
    commits = []
    ignored = 0
    for command in commands:
        identifier = command["id"]
        if identifier in seen:
            ignored += 1
            continue
        seen.append(identifier)
        trial_values = values.copy()
        trial_versions = versions.copy()
        touched = []
        operations = command["ops"] if command["op"] == "batch" else [command]
        ok = True
        for operation in operations:
            if not apply_one(trial_values, trial_versions, operation):
                ok = False
                break
            if operation["op"] in ["put", "delete"] and operation["key"] not in touched:
                touched.append(operation["key"])
        if ok:
            values = trial_values
            versions = trial_versions
            accepted.append(identifier)
            commits.append({"id": identifier, "writes": sorted(touched), "version_sum": sum([trial_versions.get(key, 0) for key in touched])})
        else:
            rejected.append(identifier)
    return {"values": values, "versions": versions, "accepted": accepted, "rejected": rejected, "ignored": ignored, "commits": commits}
'''

# Every mutation remains executable; independent examples exercise the defect.
MUTATIONS = (
    ("seen.append(identifier)", "pass", "delayed_seen"),
    ("        else:\n            rejected.append(identifier)", "        else:\n            values = trial_values\n            versions = trial_versions\n            rejected.append(identifier)", "rollback"),
    ("values.pop(key)\n        versions[key] = current + 1", "values.pop(key)\n        versions.pop(key, 0)", "tombstone"),
    ("    if command[\"exists\"] != (key in values):", "    versions[key] = current + 1\n    if command[\"exists\"] != (key in values):", "checks_write"),
    ("expected != current", "expected != values.get(key, 0)", "value_as_revision"),
    ("if key not in values:\n            return False", "if key not in values:\n            return True", "missing_delete"),
    ('operation["op"] in ["put", "delete"]', 'operation["op"] in ["put", "delete", "check"]', "audit_reads"),
    ("versions[key] = current + 1", "versions[key] = current", "put_revision"),
    ("ok = True", "ok = len(operations) > 0", "empty_batch"),
)


def mutate(indices):
    source = REFERENCE
    for index in sorted(indices):
        before, after, name = MUTATIONS[index]
        # Mutate the put revision first-occurrence site only. Composite edits
        # elsewhere retain their unique contextual anchors.
        assert before in source, name
        source = source.replace(before, after, 1)
        if name == "delayed_seen":
            source = source.replace("        if ok:\n", "        if ok:\n            seen.append(identifier)\n", 1)
    return source


def initial(seed, difficulty):
    rng = random.Random(int.from_bytes(hashlib.sha256(f"kv-repair-v1|{seed}".encode()).digest(), "big"))
    return mutate(rng.sample(range(len(MUTATIONS)), 2 if difficulty == 1 else 4))


def _oracle_operation(state, operation):
    values, revisions = state
    op = operation["op"]
    if op not in ("put", "delete", "check"):
        return None
    key = operation["key"]
    wanted = operation["expect"]
    if wanted is not None and revisions.get(key, 0) != wanted:
        return None
    if op == "check":
        if operation["exists"] is not (key in values):
            return None
        if operation["exists"] and values[key] != operation["value"]:
            return None
        return (dict(values), dict(revisions)), None
    if op == "delete" and key not in values:
        return None
    new_values, new_revisions = dict(values), dict(revisions)
    if op == "delete":
        del new_values[key]
    else:
        new_values[key] = operation["value"]
    new_revisions[key] = revisions.get(key, 0) + 1
    return (new_values, new_revisions), key


def reference(args):
    initial_values, commands = args
    state = dict(initial_values), dict.fromkeys(initial_values, 0)
    seen, accepted, rejected, commits = set(), [], [], []
    ignored = 0
    for command in commands:
        identifier = command["id"]
        if identifier in seen:
            ignored += 1
            continue
        seen.add(identifier)
        sequence = command["ops"] if command["op"] == "batch" else (command,)
        pending, writes = state, set()
        for operation in sequence:
            applied = _oracle_operation(pending, operation)
            if applied is None:
                rejected.append(identifier)
                break
            pending, key = applied
            if key is not None:
                writes.add(key)
        else:
            state = pending
            accepted.append(identifier)
            commits.append(dict(id=identifier, writes=sorted(writes),
                                version_sum=sum(state[1].get(k, 0) for k in writes)))
    return dict(values=state[0], versions=state[1], accepted=accepted,
                rejected=rejected, ignored=ignored, commits=commits)


def _operation(kind, key, expected=None, value=0, exists=True):
    result = {"op": kind, "key": key, "expect": expected}
    if kind == "put":
        result["value"] = value
    if kind == "check":
        result.update(exists=exists, value=value)
    return result


def _witness(rng, mode):
    keys = ["k" + str(x) for x in rng.sample(range(100000), 4)]
    ids = ["c" + str(x) for x in rng.sample(range(100000), 8)]
    a, b, c, d = keys; value = rng.randint(3, 30)
    initial_values = {a: value}
    def event(i, operation):
        return {"id": ids[i], **operation}
    def batch(i, operations):
        return event(i, {"op": "batch", "ops": operations})
    put = lambda key, rev, v: _operation("put", key, rev, v)
    delete = lambda key, rev: _operation("delete", key, rev)
    check = lambda key, rev, v=0, exists=True: _operation("check", key, rev, v, exists)
    if mode == 0:
        commands = [event(0, {"op": "unknown"}), event(0, put(b, 0, 9)),
            event(1, put(a, 0, value+1)), event(1, put(c, 0, 4)),
            event(2, check(a, 1, value+1))]
    elif mode == 1:
        commands = [batch(0, [put(a, 0, value+5), check(b, None, 8)]),
            event(1, check(a, 0, value)), batch(2, [put(b, 0, 3), delete(a, 0)]),
            event(0, put(c, 0, 10))]
    elif mode == 2:
        commands = [event(0, delete(a, 0)), event(1, put(a, 1, value)),
            event(2, delete(c, 0)), event(3, put(a, 2, value)),
            event(4, check(a, 3, value))]
    elif mode == 3:
        commands = [batch(0, [put(b, 0, 2), check(b, 1, 2), put(b, 1, 3), delete(a, 0)]),
            event(1, check(b, 2, 3)), event(2, delete(b, 2)),
            event(3, check(b, 3, exists=False)), event(4, put(b, 3, 7))]
    elif mode == 4:
        commands = [batch(0, []), event(1, check(c, 0, exists=False)),
            event(2, put(a, 0, value)), event(3, check(a, 1, value)),
            event(1, {"op": "unknown"})]
    else:
        commands = [batch(0, [put(a, 0, value+1), {"op": "unknown"}]),
            event(0, put(a, 0, 7)), event(1, {"op": "unknown"}), batch(1, []),
            batch(2, [check(a, 0, value)]), event(3, delete(d, 0)), event(4, put(d, 0, 6))]
    return [initial_values, commands]


def _random_operation(rng, keys, state):
    values, revisions = state
    kind = rng.choice(["put", "put", "delete", "check", "check", "unknown"])
    if kind == "unknown":
        return {"op": kind}
    key = rng.choice(keys); current = revisions.get(key, 0)
    expected = rng.choice([None, current, current, current+1])
    exists = (key in values) if rng.randrange(3) else (key not in values)
    value = values.get(key, rng.randint(-9, 9)) if kind == "check" and rng.randrange(3) else rng.randint(-9, 9)
    return _operation(kind, key, expected, value, exists)


def inputs(rng, count):
    for index in range(count):
        if index < 6:
            yield _witness(rng, index)
            continue
        keys = ["k" + str(x) for x in rng.sample(range(100000), 8)]
        initial_values = {k: rng.randint(-9, 9) for k in keys[:3]}
        commands = []
        for i in range(16):
            old = reference([initial_values, commands])
            state = old["values"], old["versions"]
            identifier = rng.choice(commands)["id"] if commands and rng.randrange(5) == 0 else "c" + str(rng.randrange(1000000))
            if rng.randrange(3) == 0:
                ops, tentative = [], state
                for _ in range(rng.randrange(5)):
                    operation = _random_operation(rng, keys, tentative); ops.append(operation)
                    applied = _oracle_operation(tentative, operation)
                    if applied is not None:
                        tentative = applied[0]
                command = {"id": identifier, "op": "batch", "ops": ops}
            else:
                command = {"id": identifier, **_random_operation(rng, keys, state)}
            commands.append(command)
        yield [initial_values, commands]
