"""Native controls for controlled repair paths, not model performance tests."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("repair_paths", ROOT / "scripts/audit-software-repair-paths.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize("task_id", MODULE.TASKS)
def test_native_endpoints_and_monotonic_exact_full_control(task_id):
    result = MODULE.audit(task_id, 1840000)
    assert result["variants"][0]["reward"] == 0
    assert result["variants"][-1]["reward"] == 1
    assert all(not v[split]["errors"] for v in result["variants"] for split in ("public", "hidden"))
    assert all(0 <= v["reward"] <= 1 for v in result["variants"])


def test_function_repair_changes_only_selected_function():
    source = "def a():\n    return 0\n\ndef b():\n    return 0\n"
    reference = source.replace("return 0", "return 1")
    repaired = MODULE.functions(MODULE.repair(source, reference, ["a"]))
    assert repaired["a"] == MODULE.functions(reference)["a"]
    assert repaired["b"] == MODULE.functions(source)["b"]
    with pytest.raises(ValueError):
        MODULE.repair(source, reference, ["absent"])


def test_semantic_identity_preserves_boolean_and_list_types():
    assert not MODULE.exact(True, 1)
    assert not MODULE.exact([1], (1,))
    assert MODULE.exact({"a": [1, False]}, {"a": [1, False]})


@pytest.mark.parametrize("seed", [1850000, 1850001, 1850002, 1850003])
def test_prerequisite_stages_share_cases_and_only_one_repair_is_needed(seed):
    from repair_env.tasks import make_task, TRAINING_TASK_IDS
    from repair_env import ignore_repair

    primary = make_task("software_repair-ignore-d2", seed)
    assert primary.initial_source.endswith(ignore_repair.SCAFFOLD)
    for level, missing in [(3, "classify_ignore"), (4, "rule_mode")]:
        stage = make_task(f"software_repair-ignore-d{level}", seed)
        assert stage.public == primary.public and stage.hidden == primary.hidden
        assert stage.reference_source == primary.reference_source
        a = MODULE.audit(stage.task_id, seed)
        assert a["changed_functions"] == [missing]
        assert a["variants"][0]["reward"] == 0
        assert a["variants"][1]["reward"] == 1
        assert all(not v[s]["errors"] for v in a["variants"] for s in ("public", "hidden"))
        assert stage.task_id not in TRAINING_TASK_IDS
    assert len(TRAINING_TASK_IDS) == 8
