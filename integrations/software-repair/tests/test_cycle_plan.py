import copy

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
