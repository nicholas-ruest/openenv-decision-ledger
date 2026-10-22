"""Original seeded Python repair tasks; no Arena evaluation tasks or answers."""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from . import (
    hard_tasks, cycle_plan, release_plan, replay_curriculum, merge_curriculum,
    release_curriculum,
    release_synthesis,
    kv_repair,
)

FAMILIES = ("clamp", "overlap", "chunks", "unique", "counts", "prefix") + hard_tasks.FAMILIES
TASK_IDS = [f"software_repair-{family}-d{d}" for family in FAMILIES for d in (1, 2)]
TASK_IDS.append("software_repair-plan-d3")
TASK_IDS.append("software_repair-plan-d4")
TASK_IDS.append("software_repair-release-d1")
TASK_IDS.append("software_repair-release-d2")
TASK_IDS.append("software_repair-release-d3")
TASK_IDS.append("software_repair-release-d4")
TASK_IDS.append("software_repair-replay-d3")
TASK_IDS.append("software_repair-merge-d3")
TASK_IDS.extend(("software_repair-kv-d1", "software_repair-kv-d2"))
TRAINING_TASK_IDS = [f"software_repair-{family}-d{d}" for family in hard_tasks.FAMILIES for d in (1, 2)]
SOURCE_PATH = "src/solution.py"


@dataclass(frozen=True)
class Case:
    args: list
    expected: object


@dataclass(frozen=True)
class Task:
    task_id: str
    seed: int
    entrypoint: str
    instructions: str
    initial_source: str
    reference_source: str
    public: tuple[Case, ...]
    hidden: tuple[Case, ...]


def reference(family, args):
    """Trusted independent specification; never exposed as an environment tool."""
    if family == "kv":
        return kv_repair.reference(args)
    if family == "clamp":
        value, lo, hi = args
        return min(hi, max(lo, value))
    if family == "overlap":
        a, b, c, d = args
        return max(0, min(b, d) - max(a, c))
    if family == "chunks":
        values, size = args
        return [] if size <= 0 else [values[i:i + size] for i in range(0, len(values), size)]
    if family == "unique":
        return list(dict.fromkeys(args[0]))
    if family == "counts":
        return {value: args[0].count(value) for value in set(args[0])}
    if family == "prefix":
        values = args[0]
        return [sum(values[:i]) for i in range(1, len(values) + 1)]
    return hard_tasks.reference(family, args)


_SPECS = {
    "clamp": ("clamp", "Clamp value to the inclusive interval [lo, hi], where lo <= hi.",
              "def clamp(value, lo, hi):\n    if value < lo:\n        return lo\n    if value > hi:\n        return hi\n    return value\n"),
    "overlap": ("overlap_length", "Return the length of intersection of half-open integer intervals [a,b) and [c,d). Inputs satisfy a<=b and c<=d; touching or empty intervals have zero overlap.",
                "def overlap_length(a, b, c, d):\n    return max(0, min(b, d) - max(a, c))\n"),
    "chunks": ("chunks", "Partition values in order into lists of size at most size, retaining the final short chunk. Return [] when size<=0. Do not mutate the input.",
               "def chunks(values, size):\n    if size <= 0:\n        return []\n    result = []\n    for i in range(0, len(values), size):\n        result.append(values[i:i + size])\n    return result\n"),
    "unique": ("stable_unique", "Return a list containing each integer once, in order of first appearance. Do not sort or mutate the input.",
               "def stable_unique(values):\n    result = []\n    for value in values:\n        if value not in result:\n            result.append(value)\n    return result\n"),
    "counts": ("counts", "Return a dictionary mapping every string present in values to its number of occurrences. Empty input produces {}. Do not mutate input.",
               "def counts(values):\n    result = {}\n    for value in values:\n        result[value] = result.get(value, 0) + 1\n    return result\n"),
    "prefix": ("prefix_sums", "Return running inclusive sums of the integer list: output[i]=sum(values[0:i+1]). Preserve length and order, including negative values; empty input gives [].",
               "def prefix_sums(values):\n    total = 0\n    result = []\n    for value in values:\n        total = total + value\n        result.append(total)\n    return result\n"),
}
_SPECS.update(hard_tasks.SPECS)
_SPECS["kv"] = ("replay_store", kv_repair.INSTRUCTIONS, kv_repair.REFERENCE)


def _initial(family, source, difficulty, seed=None):
    if family == "kv":
        return kv_repair.initial(seed, difficulty)
    if family in ("replay", "merge") and difficulty == 3:
        return hard_tasks.initial(family, source, 2)
    if family == "release":
        if difficulty == 4:
            return release_synthesis.initial()
        return release_plan.initial(seed)
    if family == "plan" and difficulty == 4:
        return cycle_plan.mutated_initial(seed)
    if family == "plan" and difficulty == 3:
        return cycle_plan.INITIAL
    if family == "clamp":
        source = source.replace("return lo", "return 0")
        return source.replace("return hi", "return lo") if difficulty == 2 else source
    if family == "overlap":
        source = source.replace("- max(a, c)", "- max(a, c) + 1")
        return source.replace("min(b, d)", "max(b, d)") if difficulty == 2 else source
    if family == "chunks":
        source = source.replace("i + size]", "i + size - 1]")
        return source.replace("len(values), size", "len(values) - 1, size") if difficulty == 2 else source
    if family == "unique":
        source = source.replace("return result", "return sorted(result)")
        return source.replace("not in result", "in result") if difficulty == 2 else source
    if family == "counts":
        source = source.replace("get(value, 0)", "get(value, 1)")
        return source.replace("+ 1", "+ 2") if difficulty == 2 else source
    if family == "prefix":
        source = source.replace("total = total + value", "total = value")
        return source.replace("total = value\n        result.append(total)",
                              "result.append(total)\n        total = value") if difficulty == 2 else source
    return hard_tasks.initial(family, source, difficulty)


def _inputs(family, rng, count, difficulty, *, visible=False):
    if family == "kv":
        for args in kv_repair.inputs(rng, count):
            yield Case(args, kv_repair.reference(args))
        return
    if family == "merge" and difficulty == 3:
        for args in merge_curriculum.inputs(rng, count):
            yield Case(args, hard_tasks.reference(family, args))
        return
    if family == "replay" and difficulty == 3:
        for args in replay_curriculum.inputs(rng, count):
            yield Case(args, hard_tasks.reference(family, args))
        return
    if family == "release":
        if difficulty in (3, 4):
            generated = release_curriculum.generalized_inputs(rng, count, visible=visible)
        else:
            generator = release_curriculum.inputs if difficulty == 2 else release_plan.inputs
            generated = generator(rng, count)
        for args in generated:
            yield Case(args, release_plan.reference(args))
        return
    if family == "plan" and difficulty in (3, 4):
        generated = (cycle_plan.variant_inputs(rng, count, visible=visible) if difficulty == 4
                     else cycle_plan.inputs(rng, count))
        for args in generated:
            yield Case(args, cycle_plan.reference(args))
        return
    if family in hard_tasks.FAMILIES:
        for args in hard_tasks.inputs(family, rng, count, difficulty):
            yield Case(args, reference(family, args))
        return
    for i in range(count):
        if family == "clamp":
            lo = rng.randint(2, 40)
            hi = lo + rng.randint(1, 30)
            value = (lo - rng.randint(1, 10), lo, (lo + hi) // 2, hi,
                     hi + rng.randint(1, 10))[i % 5]
            args = [value, lo, hi]
        elif family == "overlap":
            a = rng.randint(-30, 30)
            b = a + rng.randint(0, 15)
            c = (b, a, a - 4, b + 1)[i % 4]
            args = [a, b, c, c + rng.randint(0, 15)]
        else:
            length = [0, 1, 3, 7, 12 + 4 * difficulty][i % 5]
            values = [rng.randint(-6, 6) for _ in range(length)]
            if family == "counts":
                values = ["item_" + str(abs(x) % 5) for x in values]
            args = [values]
            if family == "chunks":
                args += [(-1, 0, 1, 2, 5, 100)[i % 6]]
        yield Case(args, reference(family, args))


def make_task(task_id, seed):
    if task_id not in TASK_IDS or type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError("known repair task ID and unsigned64 seed required")
    _, family, level = task_id.split("-")
    difficulty = int(level[1:])
    # The synthesis/control comparison intentionally shares case inputs and the
    # oracle while changing the original source. Existing d3 stays byte-frozen.
    case_task_id = ("software_repair-release-d3" if task_id == "software_repair-release-d4" else
                    "software_repair-kv-d1" if task_id == "software_repair-kv-d2" else task_id)
    material = f"decision-ledger-code-repair-v1|{case_task_id}|{seed}"
    # Independent streams: neither hidden inputs nor answers derive from public tests.
    public_rng = random.Random(int.from_bytes(hashlib.sha256((material + "|public").encode()).digest(), "big"))
    hidden_rng = random.Random(int.from_bytes(hashlib.sha256((material + "|hidden").encode()).digest(), "big"))
    if family == "release":
        name, instructions, source = "plan_release", release_plan.INSTRUCTIONS, release_plan.REFERENCE
        if difficulty == 4:
            instructions += release_synthesis.INSTRUCTIONS
    else:
        name, instructions, source = ("build_plan", cycle_plan.INSTRUCTIONS, cycle_plan.REFERENCE) if family == "plan" and difficulty in (3, 4) else _SPECS[family]
    if family == "plan" and difficulty == 4:
        instructions += " Existing code has several semantic defects. Visible examples do not cover every graph shape in the contract; reason about the complete specification."
    case_id = hashlib.sha256(material.encode()).hexdigest()[:12]
    initial = f"# Repair case {case_id}; {family} level {difficulty}\n" + _initial(family, source, difficulty, seed)
    public = tuple(_inputs(family, public_rng, 6, difficulty, visible=True))
    seen = {json.dumps(c.args, sort_keys=True) for c in public}
    hidden = []
    for case in _inputs(family, hidden_rng, 600, difficulty):
        signature = json.dumps(case.args, sort_keys=True)
        if signature not in seen:
            seen.add(signature)
            hidden.append(case)
        if len(hidden) == 30:
            break
    if len(hidden) != 30:
        raise ValueError("insufficient disjoint hidden cases")
    return Task(task_id, seed, name, instructions, initial, source, public, tuple(hidden))


def compact_literal(value):
    """Render Python fixture values without optional separator whitespace."""
    if type(value) is list:
        return "[" + ",".join(map(compact_literal, value)) + "]"
    if type(value) is tuple:
        items = ",".join(map(compact_literal, value))
        return "(" + items + ("," if len(value) == 1 else "") + ")"
    if type(value) is dict:
        return "{" + ",".join(compact_literal(k) + ":" + compact_literal(v)
                              for k, v in value.items()) + "}"
    if type(value) not in (str, int, bool, type(None)):
        raise TypeError("unsupported public fixture literal")
    return repr(value)


def visible_files(task):
    cases = [(case.args, case.expected) for case in task.public]
    test_source = "import pytest\nfrom solution import " + task.entrypoint + "\n\n"
    test_source += "@pytest.mark.parametrize('args,expected', " + compact_literal(cases) + ")\n"
    test_source += "def test_contract(args, expected):\n    assert " + task.entrypoint + "(*args) == expected\n"
    readme = (task.instructions + "\nEdit src/solution.py, run test, inspect failures, and submit. "
              "This README is already in reset.prompt. Start with read path 'src/solution.py'; "
              'send the action instance {"op":"read","path":"src/solution.py"}, never the action schema. '
              'Later {"op":"test"} runs tests and {"op":"submit"} ends the episode. '
              "Run test for feedback, then read its case_path (tests/test_public.py#case=N, N=1..6) for one full example. "
              "Reading tests/test_public.py returns all six examples. Read path '*' includes all files and repeats this README. "
              "For a local fix use op='patch', path='src/solution.py', search=the exact old text, replacement=the new text. "
              "Search must match exactly once; empty, missing, ambiguous or oversized patches leave the module unchanged. Full-file write is also available. "
              "Only src/solution.py is writable. Tests shown here are examples; final grading uses fresh hidden cases. "
              "Reward requires improving hidden test results over the original broken module; unchanged, formatting-only and non-improving edits earn zero. "
              "Python subset: one to four top-level named functions, return/assign/if/for/while, lists/dicts, indexing/slices, integer arithmetic/comparisons, "
              "len/min/max/sum/abs/sorted/list/range/set/dict/tuple/enumerate/zip/any/all, comprehensions, break/continue, bounded lazy generator expressions, integer powers/bitops and set union/intersection, list append/pop/sort/reverse/remove/copy/extend, set.add/remove/discard/copy/update/union/intersection/difference and dict get/pop/items/keys/values/copy. Internal dictionary tuple keys are supported; returned values must be JSON-serializable. Single-underscore helper/local names are allowed; function call depth is limited to16. No imports, yield/async, nested functions, "
              "exceptions, decorators, filesystem or shell. Limits: 8192 source bytes,2048 AST nodes,128 collection items,80000 execution steps/case. "
              "Visible tests use the same bounded interpreter as hidden tests; tests are not executed by host pytest in the environment.")
    return {SOURCE_PATH: task.initial_source, "tests/test_public.py": test_source,
            "README.md": readme, "pyproject.toml": "[project]\nname = 'repair-case'\nversion = '0.0.1'\n\n[tool.pytest.ini_options]\npythonpath = ['src']\n"}


def task_fingerprint(task):
    return hashlib.sha256(json.dumps({"id": task.task_id, "seed": task.seed,
        "initial": task.initial_source, "public": [(c.args, c.expected) for c in task.public],
        "hidden": [(c.args, c.expected) for c in task.hidden]}, sort_keys=True).encode()).hexdigest()
