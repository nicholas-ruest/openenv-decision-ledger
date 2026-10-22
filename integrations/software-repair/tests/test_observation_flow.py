import ast
import importlib.util
import json
from pathlib import Path

import pytest

from repair_env.environment import RepairAction, RepairEnvironment


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("saved_replay", ROOT / "scripts/replay_saved.py")
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)


def test_reset_documents_function_limit_and_direct_file_reads():
    env = RepairEnvironment()
    reset = env.reset(task_id="software_repair-release-d1", seed=1010000)
    assert "one to sixteen top-level named functions" in reset.prompt
    assert "Start with read path 'src/solution.py'" in reset.prompt
    direct = env.step(RepairAction(op="read", path="src/solution.py"))
    assert direct.content == env._task.initial_source
    workspace = json.loads(env.step(RepairAction(op="read", path="*")).content)
    assert workspace == env._files  # All original files remain accessible.


def test_reset_action_examples_are_valid_instances_without_giving_a_repair():
    env = RepairEnvironment()
    reset = env.reset(task_id="software_repair-merge-d3", seed=1086000)
    for text in ('{"op":"read","path":"src/solution.py"}',
                 '{"op":"test"}', '{"op":"submit"}'):
        assert text in reset.prompt
        action = RepairAction.model_validate_json(text)
        assert action.op in ("read", "test", "submit")
    assert "never the action schema" in reset.prompt
    assert env._files["src/solution.py"] == env._task.initial_source


def test_compact_failure_feedback_retains_results_and_visible_inputs():
    env = RepairEnvironment()
    env.reset(task_id="software_repair-release-d1", seed=1010000)
    tested = json.loads(env.step(RepairAction(op="test")).content)
    detailed = [row for row in tested["tests"] if "expected" in row]
    assert len(detailed) == 2
    for row in detailed:
        case = env._task.public[row["test"] - 1]
        assert row["expected"] == case.expected
        assert "actual" in row and "args" not in row
    full = env.step(RepairAction(op="read", path="tests/test_public.py"))
    fixture = ast.parse(full.content).body[2].decorator_list[0].args[1]
    assert ast.literal_eval(fixture) == [(c.args, c.expected) for c in env._task.public]


def saved_row():
    from repair_env.tasks import visible_files
    env = RepairEnvironment()
    reset = env.reset(task_id="software_repair-counts-d2", seed=1020000)
    messages = [{"role": "system", "content": "fixture"},
                {"role": "user", "content": reset.model_dump_json()}]
    action = RepairAction(op="write", path="src/solution.py", content=env._task.reference_source)
    observation = env.step(action)
    messages += [{"role": "assistant", "content": action.model_dump_json()},
                 {"role": "user", "content": observation.model_dump_json()},
                 {"role": "assistant", "content": '{"op":"write","content":'}]
    return {"task_id": env._task.task_id, "seed": env._task.seed, "sample": 0,
            "prompt_sha256": replay.digest({"reset": reset.model_dump(), "files": visible_files(env._task)}),
            "messages": messages, "failure": "completion_truncated", "reward": 0}


def test_posthoc_finish_is_separate_from_live_result_and_skips_truncated_action():
    row = saved_row()
    result = replay.replay_episode(row)
    assert result["offline_finish_reward"] == 1
    assert result["replayed_actions"] == ["write"]
    assert result["original_failure"] == "completion_truncated" and result["original_reward"] == 0
    assert not result["counts_as_new_live_solve"]
    assert row["reward"] == 0  # Input archive is unchanged.


def test_posthoc_replay_refuses_an_observation_not_produced_by_the_saved_action():
    row = saved_row()
    value = json.loads(row["messages"][3]["content"])
    value["content"] = "tampered"
    row["messages"][3]["content"] = json.dumps(value)
    with pytest.raises(ValueError, match="differs"):
        replay.replay_episode(row)
