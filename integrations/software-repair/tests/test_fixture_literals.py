"""Verify executable public fixtures preserve every typed input and expectation."""

import ast

import pytest

from repair_env.environment import exact
from repair_env.tasks import TASK_IDS, compact_literal, make_task, visible_files


@pytest.mark.parametrize("value", [
    [], {}, (), (1,), (True, None, False),
    ["spaces stay here", "quotes'\"", "line\nbreak", "é", "\\"],
    {1: (False,), "nested": [{"x": [0, -3, True, None]}]},
])
def test_literal_roundtrip_preserves_types_and_string_content(value):
    assert exact(ast.literal_eval(compact_literal(value)), value)


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_public_pytest_fixture_preserves_all_cases_and_executes(task_id):
    task = make_task(task_id, 1040000)
    source = visible_files(task)["tests/test_public.py"]
    tree = ast.parse(source)
    function = tree.body[2]
    cases = ast.literal_eval(function.decorator_list[0].args[1])
    assert exact(cases, [(c.args, c.expected) for c in task.public])
    # Run the exported test body against the independently generated reference.
    # Imports/decorators are omitted only to avoid installing a solution module.
    function.decorator_list = []
    namespace = {}
    exec(task.reference_source, namespace)
    exec(compile(ast.Module(body=[function], type_ignores=[]), "public", "exec"), namespace)
    for args, expected in cases:
        namespace["test_contract"](args, expected)
