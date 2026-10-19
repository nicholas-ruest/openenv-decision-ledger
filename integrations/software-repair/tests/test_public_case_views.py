import ast
import json

import pytest

from repair_env.environment import RepairAction, RepairEnvironment


@pytest.mark.parametrize("number", range(1, 7))
def test_public_case_view_is_exact_read_only_and_smaller_than_all_examples(number):
    env = RepairEnvironment()
    env.reset(task_id="software_repair-release-d1", seed=1030000)
    path = f"tests/test_public.py#case={number}"
    case = env._task.public[number - 1]
    observation = env.step(RepairAction(op="read", path=path))
    assert json.loads(observation.content) == {"test": number, "args": case.args, "expected": case.expected}
    full = env.step(RepairAction(op="read", path="tests/test_public.py"))
    assert len(observation.content) < len(full.content)
    fixture = ast.parse(full.content).body[2].decorator_list[0].args[1]
    assert ast.literal_eval(fixture) == [(c.args, c.expected) for c in env._task.public]
    assert env.step(RepairAction(op="write", path=path, content="changed")).error
    assert env._task.public[number - 1] == case


@pytest.mark.parametrize("path", ["tests/test_public.py#case=0", "tests/test_public.py#case=7",
    "tests/test_public.py#case=-1", "tests/test_public.py#case=01", "tests/test_public.py#case=1/../hidden",
    "tests/test_public.py#case=hidden", "tests/test_public.py#case=1extra"])
def test_case_views_reject_non_public_or_ambiguous_indices(path):
    env = RepairEnvironment()
    env.reset(task_id="software_repair-release-d1", seed=1030000)
    assert env.step(RepairAction(op="read", path=path)).error == "unknown workspace path"


def test_failure_feedback_links_only_to_the_matching_public_example():
    env = RepairEnvironment()
    env.reset(task_id="software_repair-release-d1", seed=1030000)
    results = json.loads(env.step(RepairAction(op="test")).content)
    failures = [row for row in results["tests"] if "case_path" in row]
    assert len(failures) == 2
    for row in failures:
        observation = env.step(RepairAction(op="read", path=row["case_path"]))
        example = json.loads(observation.content)
        assert example["test"] == row["test"] and example["expected"] == row["expected"]
        assert example["args"] == env._task.public[row["test"] - 1].args
