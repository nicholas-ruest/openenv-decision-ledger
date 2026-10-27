"""Fair isolated/compound replay cases; no claim about sampled model learning."""

import importlib.util
from pathlib import Path
import random

import pytest

from repair_env import hard_tasks, replay_curriculum
from repair_env.runner import Program
from repair_env.tasks import TRAINING_TASK_IDS, make_task

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("replay_audit", ROOT / "scripts/audit-software-curriculum.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


@pytest.mark.parametrize("seed", range(1052000, 1052008))
def test_isolated_diagnostic_preserves_faults_contract_and_event_count(seed):
    old = make_task("software_repair-replay-d2", seed)
    new = make_task("software_repair-replay-d3", seed)
    assert Program(old.initial_source).fingerprint == Program(new.initial_source).fingerprint
    assert old.reference_source == new.reference_source and old.instructions == new.instructions
    assert new.task_id not in TRAINING_TASK_IDS
    assert all(len(case.args[0]) == 18 for case in old.public + old.hidden + new.public + new.hidden)
    row = audit.audit_instance(new)
    assert row["baseline"]["hidden_passed"] == 0
    assert row["reference"]["public_passed"] == 6 and row["reference"]["hidden_passed"] == 30
    assert sorted(item["formula_reward"] for item in row["controlled_variants"]) == [1 / 3, .5]
    assert all(not item["hidden_errors"] and 0 < item["public_passed"] < 6
               for item in row["controlled_variants"])


@pytest.mark.parametrize("mode", range(6))
def test_each_scenario_matches_its_isolated_or_compound_contract(mode):
    args = list(replay_curriculum.inputs(random.Random(1053000), 6))[mode]
    expected = hard_tasks.reference("replay", args)
    reference = hard_tasks.SPECS["replay"][2]
    initial = hard_tasks.initial("replay", reference, 2)
    undo = initial.replace("                pass", '                active.pop(event["target"])')
    duplicate = initial.replace("if True:", "if identifier not in seen:")
    assert Program(initial).run("replay_events", args) != expected
    assert Program(reference).run("replay_events", args) == expected
    assert (Program(undo).run("replay_events", args) == expected) == (mode in (0, 4))
    assert (Program(duplicate).run("replay_events", args) == expected) == (mode in (1, 3, 5))


def test_new_diagnostic_is_native_and_partially_repairable():
    pytest.importorskip("openenv")
    from repair_env.environment import RepairAction, RepairEnvironment

    env = RepairEnvironment()
    env.reset(task_id="software_repair-replay-d3", seed=1054000)
    assert not env.step(RepairAction(op="patch", path="src/solution.py",
                                    search="if True:", replacement="if identifier not in seen:")).error
    assert env.step(RepairAction(op="submit")).reward == .5
