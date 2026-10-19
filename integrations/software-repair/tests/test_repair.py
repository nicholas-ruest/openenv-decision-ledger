import ast
import copy
import json
from pathlib import Path

import pytest

from repair_env.environment import RepairAction, RepairEnvironment, check
from repair_env.runner import Program, Rejected
from repair_env.tasks import SOURCE_PATH, TASK_IDS, TRAINING_TASK_IDS, make_task, task_fingerprint


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_generated_tasks_have_real_defects_and_independent_controls(task_id):
    fingerprints = set()
    for seed in range(980000, 980016):
        task = make_task(task_id, seed)
        assert task == make_task(task_id, seed)
        fingerprints.add(task_fingerprint(task))
        public = {json.dumps(c.args, sort_keys=True) for c in task.public}
        hidden = [json.dumps(c.args, sort_keys=True) for c in task.hidden]
        assert len(hidden) == len(set(hidden)) == 30
        assert not public.intersection(hidden)
        before, _ = check(Program(task.initial_source), task, task.hidden)
        after, _ = check(Program(task.reference_source), task, task.hidden)
        assert before < 30 and after == 30
        # Trusted CPython is used ONLY on our own static reference fixtures.
        namespace = {}
        exec(task.reference_source, {}, namespace)
        for case in task.public + task.hidden:
            assert namespace[task.entrypoint](*copy.deepcopy(case.args)) == case.expected
    assert len(fingerprints) == 16


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_edit_test_submit_real_workflow_and_exact_reward(task_id):
    env = RepairEnvironment()
    observation = env.reset(task_id=task_id, seed=990000)
    assert not observation.done and observation.reward == 0
    initial = env.step(RepairAction(op="test"))
    assert not initial.error and json.loads(initial.content)["total"] == 6
    task = make_task(task_id, 990000)
    env.step(RepairAction(op="write", path=SOURCE_PATH, content=task.reference_source))
    tested = env.step(RepairAction(op="test"))
    assert json.loads(tested.content)["passed"] == 6
    result = env.step(RepairAction(op="submit"))
    assert result.done and result.reward == 1.0
    assert env.step(RepairAction(op="write", path=SOURCE_PATH, content="")).reward == 1


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_unchanged_empty_and_comment_only_edits_never_pay(task_id):
    for change in (None, "", "# cosmetic edit only\n"):
        env = RepairEnvironment()
        env.reset(task_id=task_id, seed=990001)
        if change is not None:
            source = change if change == "" else change + env._files[SOURCE_PATH]
            env.step(RepairAction(op="write", path=SOURCE_PATH, content=source))
        result = env.step(RepairAction(op="submit"))
        assert result.done and result.reward == 0


def test_partial_reward_requires_behavioral_improvement():
    env = RepairEnvironment()
    env.reset(task_id="software_repair-clamp-d2", seed=990002)
    partial = env._files[SOURCE_PATH].replace("return 0", "return lo")
    env.step(RepairAction(op="write", path=SOURCE_PATH, content=partial))
    result = env.step(RepairAction(op="submit"))
    assert 0 < result.reward < 1 and result.done


def test_memorizing_public_examples_does_not_solve_hidden_cases():
    env = RepairEnvironment()
    env.reset(task_id="software_repair-clamp-d2", seed=990006)
    source = "def clamp(value, lo, hi):\n"
    for case in env._task.public:
        source += f"    if [value, lo, hi] == {case.args!r}:\n        return {case.expected!r}\n"
    source += "    return 0\n"
    env.step(RepairAction(op="write", path=SOURCE_PATH, content=source))
    assert json.loads(env.step(RepairAction(op="test")).content)["passed"] == 6
    assert env.step(RepairAction(op="submit")).reward == 0


def test_export_request_is_image_bound_and_does_not_send():
    import importlib.util
    script = Path(__file__).parents[1] / "scripts/export_dataset.py"
    spec = importlib.util.spec_from_file_location("repair_export", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(ValueError):
        module.request("ghcr.io/nicholas-ruest/openenv-decision-ledger:latest")
    value = module.request("ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:" + "a" * 64)
    assert len(value["tasks"]) == 8
    assert {task["task_id"] for task in value["tasks"]} == set(TRAINING_TASK_IDS)
    assert value["schema"]["action"] == RepairAction.model_json_schema()
    assert value["finish_action"] == {"op": "submit"}
    assert all(task["completion_tokens"] == 8192 for task in value["tasks"])


@pytest.mark.parametrize("source", [
    "import os\ndef clamp(a,b,c): return os.environ",
    "def clamp(a,b,c): return open('/etc/passwd').read()",
    "def clamp(a,b,c): return a.__class__",
    "def clamp(a,b,c): return getattr(a, '__class__')",
    "def clamp(a,b,c): return eval('1')",
    "def clamp(a,b,c): return globals()",
    "def clamp(a,b,c): return [0] * 1000000000",
    "def clamp(a,b,c): return 'x' * 1000000000",
    "def clamp(a,b,c): return 2 ** 1000000000",
    "def clamp(a,b,c):\n    while True:\n        pass",
    "def clamp(a,b,c): return clamp(a,b,c)",
    "def clamp(a,b,c): return list(range(1000000000))",
    "def clamp(a,b,c): return (x for x in range(3))",
    "def clamp(a,b,c): return __import__('os')",
    "def clamp(a,b,c): return (lambda: 1)()",
    "def clamp(a,b,c):\n    try:\n        return a\n    except:\n        return 0",
])
def test_untrusted_programs_are_rejected_within_bounds(source):
    with pytest.raises((Rejected, ValueError, TypeError, OverflowError)):
        Program(source).run("clamp", [2, 1, 3])


def test_input_mutation_and_cyclic_values_rejected():
    with pytest.raises(Rejected, match="mutation"):
        Program("def f(xs):\n    xs.append(1)\n    return xs\n").run("f", [[]])
    with pytest.raises(Rejected):
        Program("def f(xs):\n    result=[]\n    result.append(result)\n    return result\n").run("f", [[]])


def test_hidden_case_inputs_and_grader_are_not_workspace_files():
    env = RepairEnvironment()
    observation = env.reset(task_id="software_repair-counts-d2", seed=990003)
    assert sorted(observation.files) == ["README.md", "pyproject.toml", "src/solution.py", "tests/test_public.py"]
    before = copy.deepcopy(env._task.hidden)
    public = json.loads(env.step(RepairAction(op="test")).content)
    assert [row["args"] for row in public["tests"]] == [case.args for case in env._task.public]
    assert env._task.hidden == before
    for path in ("../tasks.py", "/proc/self/environ", "tests/test_public.py", "README.md"):
        result = env.step(RepairAction(op="write", path=path, content="hacked"))
        assert result.error and result.reward == 0
    assert env.step(RepairAction(op="read", path="../runner.py")).error


def test_session_isolation_and_step_budget():
    first, second = RepairEnvironment(), RepairEnvironment()
    a = first.reset(seed=990004)
    b = second.reset(seed=990005)
    first.step(RepairAction(op="write", path=SOURCE_PATH, content=""))
    assert second._files[SOURCE_PATH] != ""
    assert a.task_id == b.task_id
    for _ in range(12):
        result = second.step(RepairAction(op="list"))
    assert result.done and result.reward == 0
    assert first.state.episode_id != second.state.episode_id


@pytest.mark.parametrize("task_id,seed", [("software_repair-clamp-d3", 1),
    (TASK_IDS[0], True), (TASK_IDS[0], -1), (TASK_IDS[0], 2**64)])
def test_invalid_reset_is_rejected(task_id, seed):
    with pytest.raises(ValueError):
        RepairEnvironment().reset(task_id=task_id, seed=seed)


def test_source_and_value_limits():
    with pytest.raises(Rejected):
        Program("#" * 8193)
    with pytest.raises(Rejected):
        Program("def f(): return " + repr("a" * 2049)).run("f", [])


def test_no_candidate_eval_exec_or_subprocess_in_runner():
    tree = ast.parse(Path(__file__).parents[1].joinpath("repair_env/runner.py").read_text())
    calls = [node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
    assert not set(calls).intersection({"eval", "exec", "compile", "open", "getattr", "__import__"})


def test_bounded_algorithm_features_and_comprehension_scope():
    source = '''def f(xs):
    x = 99
    values = [x * 2 for x in xs if x > 0]
    mapping = {i: value for i, value in enumerate(values)}
    unique = {value for value in values}
    unique.add(7)
    result = []
    for value in sorted(unique):
        if value == 4:
            continue
        result.append(value)
        if value == 7:
            break
    mapping.pop(0, None)
    return [result, list(mapping.items()), x, 2 ** 7, 3 << 2, 7 & 3]
'''
    assert Program(source).run("f", [[-1, 2, 3, 2]]) == [[6, 7], [(1, 6), (2, 4)], 99, 128, 12, 3]


@pytest.mark.parametrize("source", [
    "def f(): return [x for x in range(128) for y in range(128)]",
    "def f(): return 1 << 127 + 1",
    "def f(): return 99 ** 127",
    "def f():\n    break",
    "def f(): return [x async for x in []]",
])
def test_new_algorithm_features_preserve_resource_bounds(source):
    with pytest.raises(Rejected):
        Program(source).run("f", [])
