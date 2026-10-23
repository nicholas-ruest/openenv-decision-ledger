import copy
import json

import pytest

from repair_env import cycle_plan
from repair_env.runner import Program, Rejected


@pytest.mark.parametrize("graph,changed,expected", [
    ({"a": ["b"], "b": ["a"], "c": ["a"], "d": []}, ["a", "missing", "missing"],
     {"order": [], "blocked": ["a", "b", "c"], "cycles": [["a", "b"]], "unknown": ["missing"]}),
    ({"a": ["b"], "b": ["a"], "c": ["a"], "d": []}, ["c"],
     {"order": ["c"], "blocked": [], "cycles": [], "unknown": []}),
    ({"a": ["a"], "b": ["a"], "c": [], "d": ["c"]}, ["a", "c"],
     {"order": ["c", "d"], "blocked": ["a", "b"], "cycles": [["a"]], "unknown": []}),
    ({"a": ["b"], "b": ["a"], "c": ["d"], "d": ["c"]}, ["a", "d"],
     {"order": [], "blocked": ["a", "b", "c", "d"], "cycles": [["a", "b"], ["c", "d"]], "unknown": []}),
    ({"z": [], "a": ["z"], "b": [], "c": ["a", "b"]}, ["z", "b"],
     {"order": ["b", "z", "a", "c"], "blocked": [], "cycles": [], "unknown": []}),
    ({"a": []}, ["bad"], {"order": [], "blocked": [], "cycles": [], "unknown": ["bad"]}),
])
def test_cycle_contract_has_independent_handwritten_expectations(graph, changed, expected):
    before = copy.deepcopy([graph, changed])
    assert cycle_plan.reference([graph, changed]) == expected
    assert Program(cycle_plan.REFERENCE).run("build_plan", [graph, changed]) == expected
    assert [graph, changed] == before


def test_lazy_generator_short_circuit_outer_binding_and_yield_limit():
    assert Program("def f(xs): return any(1 // x for x in xs)").run("f", [[1, 0]])
    assert len(Program("def f(): return list(x for x in range(128))").run("f", [])) == 128
    source = "def f(xs):\n    n=1\n    g=(x+n for x in xs)\n    n=2\n    return list(g)"
    assert Program(source).run("f", [[1, 2]]) == [3, 4]
    with pytest.raises(Rejected, match="yield limit"):
        Program("def f(): return sum(x for x in range(128) for y in range(2))").run("f", [])


def test_generator_outer_iterator_is_created_immediately():
    source = "def f():\n    d={'a':1}\n    g=(x for x in d)\n    d['b']=2\n    return list(g)"
    with pytest.raises(RuntimeError):
        Program(source).run("f", [])


def test_standard_private_helpers_and_bounded_collection_methods():
    source = '''def _sum(_xs, _i):
    if _i == len(_xs):
        return 0
    return _xs[_i] + _sum(_xs, _i+1)
def f(xs):
    copied = xs.copy()
    copied.extend([9])
    seen = set(xs)
    seen.update([10])
    return [_sum(xs, 0), copied, sorted(seen | {11}), sorted(seen & {10})]
'''
    assert Program(source).run("f", [list(range(9))]) == [36, list(range(10)), list(range(9)) + [10, 11], [10]]
    with pytest.raises(Rejected, match="update limit"):
        Program("def f():\n    xs=list(range(128))\n    xs.extend([1])\n    return xs").run("f", [])


def test_natural_solution_size_is_supported_but_larger_ast_remains_bounded():
    assert Program("def f():\n" + "    a=1\n" * 180 + "    return a").run("f", []) == 1
    with pytest.raises(Rejected, match="AST node limit2048"):
        Program("def f():\n" + "    a=1\n" * 600 + "    return a")


def test_set_method_forms_match_bounded_set_operators():
    source = "def f():\n    a={1,2}\n    return [sorted(a.union({3}, [4])), sorted(a.intersection([2,3])), sorted(a.difference({1}))]"
    assert Program(source).run("f", []) == [[1,2,3,4], [2], [2]]


@pytest.mark.parametrize("seed", [994000, 994100, 994200, 994300])
def test_realistic_planner_has_repairable_semantic_defects_without_execution_failures(seed):
    from repair_env.environment import RepairAction, RepairEnvironment, check
    env = RepairEnvironment()
    env.reset(task_id="software_repair-plan-d3", seed=seed)
    baseline, outcomes = check(Program(env._task.initial_source), env._task,
                               env._task.hidden, details=True)
    assert 0 < baseline < len(outcomes)
    assert all(row["error"] is None for row in outcomes)
    # Correct only the cycle ordering defect: a real, useful but incomplete fix.
    partial = env._task.initial_source.replace('"cycles": sorted(cycles)[::-1]',
                                                '"cycles": sorted(cycles)')
    env.step(RepairAction(op="write", path="src/solution.py", content=partial))
    assert 0 < env.step(RepairAction(op="submit")).reward < 1
    env.reset(task_id="software_repair-plan-d3", seed=seed)
    env.step(RepairAction(op="write", path="src/solution.py", content=cycle_plan.REFERENCE))
    assert env.step(RepairAction(op="submit")).reward == 1


def test_exact_patch_can_complete_a_repair_without_full_file_generation():
    from repair_env.environment import RepairAction, RepairEnvironment
    env = RepairEnvironment()
    env.reset(task_id="software_repair-clamp-d1", seed=998000)
    result = env.step(RepairAction(op="patch", path="src/solution.py",
                                   search="return 0", replacement="return lo"))
    assert not result.error
    assert env.step(RepairAction(op="submit")).reward == 1


@pytest.mark.parametrize("path,search,replacement", [
    ("README.md", "Repair", "Changed"),
    ("src/solution.py", "", "ignored"),
    ("src/solution.py", "not present", "ignored"),
    ("src/solution.py", " ", "ignored"),
    ("src/solution.py", "return 0", "é" * 4100),
])
def test_invalid_patch_is_atomic_and_preserves_the_module(path, search, replacement):
    from repair_env.environment import RepairAction, RepairEnvironment
    env = RepairEnvironment()
    env.reset(task_id="software_repair-clamp-d1", seed=998100)
    before = env._files.copy()
    assert env.step(RepairAction(op="patch", path=path, search=search,
                                 replacement=replacement)).error
    assert env._files == before


def test_patch_does_not_bypass_the_interpreter():
    from repair_env.environment import RepairAction, RepairEnvironment
    env = RepairEnvironment()
    env.reset(task_id="software_repair-clamp-d1", seed=998200)
    env.step(RepairAction(op="patch", path="src/solution.py",
                         search="return 0", replacement="return open('private')"))
    tested = json.loads(env.step(RepairAction(op="test")).content)
    assert tested["passed"] < tested["total"]
    assert any("call unsupported" in (case["error"] or "") for case in tested["tests"])
    assert env.step(RepairAction(op="submit")).reward == 0


def test_three_local_planner_patches_repair_the_actual_workspace():
    from repair_env.environment import RepairAction, RepairEnvironment
    env = RepairEnvironment()
    env.reset(task_id="software_repair-plan-d3", seed=998300)
    edits = [
        ("unknown = sorted([name for name in changed if name not in graph])",
         "unknown = sorted(set([name for name in changed if name not in graph]))"),
        ("order.append(max(ready))", "order.append(min(ready))"),
        ('"cycles": sorted(cycles)[::-1]', '"cycles": sorted(cycles)'),
    ]
    for search, replacement in edits:
        assert not env.step(RepairAction(op="patch", path="src/solution.py",
                                        search=search, replacement=replacement)).error
    assert env.step(RepairAction(op="submit")).reward == 1
