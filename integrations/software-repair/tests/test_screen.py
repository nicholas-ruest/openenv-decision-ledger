import importlib.util
import json
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import threading
import time
import urllib.error

import pytest


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("repair_screen", ROOT / "scripts/repair-signal-screen.py")
screen = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(screen)


def receipt(tmp_path, **updates):
    data = {"checked_at": datetime.now(timezone.utc).isoformat(), "screen_cap_usd": 2,
            "prior_spend_usd": 5, "prepaid_balance_usd": 15, "total_authorized_usd": 50}
    data.update(updates)
    path = tmp_path / "private-budget.json"
    path.write_text(json.dumps(data))
    return path


@pytest.mark.parametrize("change", [{"screen_cap_usd": 3}, {"prepaid_balance_usd": 1},
    {"prior_spend_usd": 49}, {"checked_at": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()}])
def test_budget_refuses_stale_or_insufficient_allocations(tmp_path, change):
    with pytest.raises(ValueError):
        screen.DollarReservations(receipt(tmp_path, **change))


def test_reservations_are_persistent_not_refunded_and_once_only(tmp_path):
    path = receipt(tmp_path)
    budget = screen.DollarReservations(path)
    prices = {"input": 1, "output": 3}
    cost = budget.reserve("call-one", 1000, 1000, prices)
    assert cost > 0
    with pytest.raises(ValueError, match="duplicate"):
        screen.DollarReservations(path).reserve("call-one", 1000, 1000, prices)
    with pytest.raises(ValueError, match="exhausted"):
        budget.reserve("too-large", 1_000_000, 1_000_000, prices)
    assert len(budget.ledger.read_text().splitlines()) == 1


@pytest.mark.parametrize("hours", [-1, 3])
def test_each_call_refuses_an_observation_that_expires_after_construction(tmp_path, monkeypatch, hours):
    budget = screen.DollarReservations(receipt(tmp_path))
    later = datetime.now(timezone.utc) + timedelta(hours=hours)
    class Clock:
        @staticmethod
        def now(zone):
            return later
    monkeypatch.setattr(screen, "datetime", Clock)
    with pytest.raises(ValueError, match="billing observation expired"):
        budget.reserve("late-call", 1000, 1000, {"input": 1, "output": 3})
    assert budget.ledger.read_text() == ""


def test_default_plan_cannot_contact_provider(monkeypatch, capsys):
    monkeypatch.setattr(screen, "quote", lambda *a: pytest.fail("default contacted provider"))
    assert screen.main([]) == 0
    value = json.loads(capsys.readouterr().out)
    assert not value["executed"] and value["max_calls"] == 96


def test_small_probe_cannot_skip_private_budget_admission(tmp_path, monkeypatch):
    called = []
    def refuse_receipt(path):
        called.append(path)
        raise ValueError("fresh reconciled existing inference allocation required")
    monkeypatch.setattr(screen, "DollarReservations", refuse_receipt)
    monkeypatch.setattr(screen, "quote", lambda *a: pytest.fail("provider before budget admission"))
    args = Namespace(stage="screen", profile="merge_probe", output=tmp_path / "fresh",
                     budget_receipt=tmp_path / "private.json", tokenizer=tmp_path / "tokenizer.json")
    with pytest.raises(ValueError, match="fresh reconciled"):
        screen._execute(time.monotonic() + 30, args, screen.get_profile("merge_probe", "screen"))
    assert called == [args.budget_receipt]


@pytest.mark.parametrize("failure", [None, "invalid_json_action", "completion_truncated", "missing_usage"])
def test_proxy_group_actions_and_failure_separation(tmp_path, monkeypatch, failure):
    from repair_env.tasks import _SPECS
    frozen = {"provider": {"pricing": {"input": 0.2, "output": 2.5}}}
    monkeypatch.setattr(screen, "quote", lambda *a: frozen)
    actions = [{"op": "read", "path": "*"},
        {"op": "write", "path": "src/solution.py", "content": _SPECS["counts"][2]},
        {"op": "test"}, {"op": "submit"}]
    def provider(opener, base, token, payload, timeout):
        turn = sum(message["role"] == "assistant" for message in payload["messages"])
        reply = {"id": "fixture-reply-" + str(turn), "choices": [{"message": {"content": "not-json" if failure == "invalid_json_action" else json.dumps(actions[turn])},
                              "finish_reason": "length" if failure == "completion_truncated" else "stop"}],
                 "usage": {"prompt_tokens": 100, "completion_tokens": 100, "total_tokens": 200}}
        if failure == "missing_usage":
            reply.pop("usage")
        return reply
    monkeypatch.setattr(screen.helper, "provider_call", provider)
    result = screen.episode("software_repair-counts-d2", 985000, 0, "synthetic-private-test",
        screen.helper.TokenCounter(), screen.DollarReservations(receipt(tmp_path)), frozen,
        threading.Event(), time.monotonic() + 30, "offline-fixture")
    if failure:
        assert not result["solved"] and result["failure"]
        if failure != "missing_usage":
            assert result["failure"] == failure
    else:
        assert result["solved"] and result["reward"] == 1
        assert len(result["calls"]) == 4
        assert len({call["client_call_label"] for call in result["calls"]}) == 4
        assert len({call["provider_response_id_sha256"] for call in result["calls"]}) == 4
        assert "fixture-reply-" not in json.dumps(result)
        assert not result["arena_budget_matched"] and not result["thinking_verified"]


def test_confirmation_plan_uses_disjoint_seeds_without_any_provider_call(monkeypatch, capsys):
    monkeypatch.setattr(screen, "quote", lambda *a: pytest.fail("plan contacted provider"))
    assert screen.main(["--stage", "confirm"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["stage"] == "confirm" and not plan["executed"]
    assert {seed for _, seed in plan["groups"]}.isdisjoint(seed for _, seed in screen.GROUPS)
    assert plan["max_calls"] == 96


@pytest.mark.parametrize("profile,task", [("replay_compare", "software_repair-replay-d3"),
                                        ("merge_compare", "software_repair-merge-d3")])
def test_replay_profile_plan_and_lock_precede_budget_authentication_or_provider(monkeypatch, capsys, profile, task):
    for name in ("quote", "DollarReservations"):
        monkeypatch.setattr(screen, name, lambda *a: pytest.fail("plan or lock touched admission/provider"))
    assert screen.main(["--profile", profile]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["signal_task_ids"] == [task]
    assert len(plan["groups"]) == 4 and plan["max_calls"] == 192
    assert not plan["executed"] and not plan["execution_enabled"]
    with pytest.raises(ValueError, match="plan-only"):
        screen.main(["--profile", profile, "--execute"])


@pytest.mark.parametrize("finish", [True, False, 1, 1.0])
def test_reserved_finish_requires_literal_boolean_not_numeric_coercion(tmp_path, monkeypatch, finish):
    from repair_env.tasks import _SPECS
    frozen = {"provider": {"pricing": {"input": .2, "output": 2.5}}}
    monkeypatch.setattr(screen, "quote", lambda *a: frozen)
    actions = [{"op": "write", "path": "src/solution.py", "content": _SPECS["counts"][2]},
               {"finish": finish}]
    def provider(opener, base, token, payload, timeout):
        turn = sum(message["role"] == "assistant" for message in payload["messages"])
        return {"id": f"offline-finish-fixture-{turn}", "choices": [{"message": {"content": json.dumps(actions[turn])},
            "finish_reason": "stop"}], "usage": {"prompt_tokens": 100, "completion_tokens": 100}}
    monkeypatch.setattr(screen.helper, "provider_call", provider)
    result = screen.episode("software_repair-counts-d2", 985001, 0, "offline-fixture-placeholder",
        screen.helper.TokenCounter(), screen.DollarReservations(receipt(tmp_path)), frozen,
        threading.Event(), time.monotonic() + 30, "offline-finish-fixture")
    if finish is True:
        assert result["solved"] and result["reward"] == 1 and result["failure"] is None
    else:
        assert not result["solved"] and result["failure"] == "invalid_json_action"
        assert result["reward"] == 0  # A correct saved workspace cannot erase format failure.
        assert result["termination_grading"]["terminal_reward"] == 1
        assert result["termination_grading"]["counts_as_valid_completion"] is False


@pytest.mark.parametrize("ending", ["invalid", "truncated", "budget"])
def test_failed_episode_terminal_partial_reward_is_diagnostic_only(tmp_path, monkeypatch, ending):
    from repair_env.tasks import make_task
    task = make_task("software_repair-replay-d3", 1070000)
    partial = task.initial_source.replace("if True:", "if identifier not in seen:")
    frozen = {"provider": {"pricing": {"input": .2, "output": 2.5}}}
    monkeypatch.setattr(screen, "quote", lambda *a: frozen)
    def provider(opener, base, token, payload, timeout):
        turn = sum(message["role"] == "assistant" for message in payload["messages"])
        content = json.dumps({"op": "write", "path": "src/solution.py", "content": partial}) if turn == 0 else "invalid"
        return {"id": f"offline-partial-fixture-{turn}", "choices": [{"message": {"content": content},
            "finish_reason": "length" if ending == "truncated" and turn else "stop"}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 100}}
    monkeypatch.setattr(screen.helper, "provider_call", provider)
    class ObservationOverflow:
        def count(self, text):
            return 9000
        def context(self, messages):
            return 0
    counter = ObservationOverflow() if ending == "budget" else screen.helper.TokenCounter()
    result = screen.episode(task.task_id, task.seed, 0, "offline-fixture-placeholder", counter,
        screen.DollarReservations(receipt(tmp_path)), frozen, threading.Event(),
        time.monotonic() + 30, "offline-partial-fixture")
    expected = {"invalid": "invalid_json_action", "truncated": "completion_truncated", "budget": "episode_budget_exceeded"}
    assert result["failure"] == expected[ending] and not result["solved"] and result["reward"] == 0
    diagnostic = result["termination_grading"]
    assert diagnostic["available"] and diagnostic["finish_action_sent"] and diagnostic["observed_done"]
    assert diagnostic["terminal_reward"] == .5 and not diagnostic["counts_as_valid_completion"]


def test_already_terminal_budget_failure_is_not_regraded_into_a_success(monkeypatch):
    from repair_env.environment import RepairAction, RepairEnvironment
    from repair_env.tasks import make_task
    env = RepairEnvironment()
    task = make_task("software_repair-counts-d2", 1070100)
    env.reset(task_id=task.task_id, seed=task.seed)
    env.step(RepairAction(op="write", path="src/solution.py", content=task.reference_source))
    for _ in range(11):
        last = env.step(RepairAction(op="list"))
    assert last.done and last.reward == 0 and last.error
    monkeypatch.setattr(env, "step", lambda *a: pytest.fail("terminal episode was regraded"))
    result = screen.failed_finish_diagnostic(env, last)
    assert result["terminal_reward"] == 0 and not result["finish_action_sent"]
    assert result["hidden_wrong_answers"] == 0 and not result["counts_as_valid_completion"]


@pytest.mark.parametrize("point", ["before_reset", "metric", "after_write"])
def test_internal_error_preserves_only_observed_identity_and_diagnostic_state(tmp_path, monkeypatch, point):
    from repair_env.tasks import make_task
    task = make_task("software_repair-replay-d3", 1071000)
    partial = task.initial_source.replace("if True:", "if identifier not in seen:")
    frozen = {"provider": {"pricing": {"input": .2, "output": 2.5}}}
    monkeypatch.setattr(screen, "quote", lambda *a: frozen)
    def provider(*args):
        return {"id": "internal-fixture-response", "choices": [{"message": {"content": json.dumps(
            {"op": "write", "path": "src/solution.py", "content": partial})}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 100}}
    monkeypatch.setattr(screen.helper, "provider_call", provider)
    def explode(*args, **kwargs):
        raise RuntimeError("private synthetic exception text")
    if point == "before_reset":
        monkeypatch.setattr(screen, "RepairEnvironment", explode)
    if point == "metric":
        monkeypatch.setattr(screen.helper, "metric_for", explode)
    class BrokenCounter:
        def context(self, messages):
            return 0
        count = staticmethod(explode)
    stop = threading.Event()
    row = screen.episode(task.task_id, task.seed, 2, "offline-fixture-placeholder",
        BrokenCounter() if point == "after_write" else screen.helper.TokenCounter(),
        screen.DollarReservations(receipt(tmp_path)), frozen, stop, time.monotonic() + 30,
        "offline-internal-fixture")
    assert row["failure"] == "screen_internal_failure" and row["failure_type"] == "RuntimeError"
    assert stop.is_set() and not row["solved"] and row["reward"] == 0 and row["sample"] == 2
    assert "private synthetic exception text" not in json.dumps(row)
    if point == "before_reset":
        assert row["prompt_identity_unavailable"] and not row["calls"]
        assert "messages" not in row and "prompt_sha256" not in row
    else:
        assert len(row["calls"]) == 1 and len(row["prompt_sha256"]) == 64
        assert row["calls"][0]["client_call_label"].endswith(":2:0")
        assert len(row["calls"][0]["provider_response_id_sha256"]) == 64
        assert len(row["messages"]) >= 2
        assert row["termination_grading"]["terminal_reward"] == (.5 if point == "after_write" else 0)
        assert not row["termination_grading"]["counts_as_valid_completion"]


@pytest.mark.parametrize("expire_after", ["quote", "reservation", "stop_during_reservation"])
def test_deadline_consumed_during_admission_never_contacts_provider_or_refunds(tmp_path, monkeypatch, expire_after):
    clock = [0]
    stop = threading.Event()
    monkeypatch.setattr(screen, "_now", lambda: clock[0])
    frozen = {"provider": {"pricing": {"input": .2, "output": 2.5}}}
    def quote(*args):
        assert 0 < args[2] <= 10
        if expire_after == "quote":
            clock[0] = 11
        return frozen
    monkeypatch.setattr(screen, "quote", quote)
    monkeypatch.setattr(screen.helper, "provider_call", lambda *a: pytest.fail("admitted an expired provider call"))
    budget = screen.DollarReservations(receipt(tmp_path))
    reserve = budget.reserve
    def advancing_reservation(*args):
        value = reserve(*args)
        if expire_after == "reservation":
            clock[0] = 11
        else:
            stop.set()
        return value
    monkeypatch.setattr(budget, "reserve", advancing_reservation)
    result = screen.episode("software_repair-counts-d2", 1070200, 0, "offline-fixture-placeholder",
        screen.helper.TokenCounter(), budget, frozen, stop, 10, "offline-deadline-fixture")
    assert result["failure"] == "screen_stopped" and result["calls"] == []
    if expire_after == "quote":
        assert not budget.ledger.exists()
    else:
        assert len(budget.ledger.read_text().splitlines()) == 1  # Never refund an existing reservation.


def test_cli_runs_in_owned_supervised_worker_without_admission_or_credentials(tmp_path, monkeypatch, capsys):
    def fake_execute(until, args, profile):
        args.output.mkdir()
        (args.output / "fixture.json").write_text(json.dumps({"deadline_in_future": until > time.monotonic()}))
        return 0
    monkeypatch.setattr(screen, "_execute", fake_execute)
    monkeypatch.setattr(screen, "quote", lambda *a: pytest.fail("fixture contacted provider"))
    monkeypatch.setattr(screen, "DollarReservations", lambda *a: pytest.fail("fixture touched admission"))
    output = tmp_path / "run"
    result = screen.main(["--execute", "--output", str(output), "--budget-receipt", str(tmp_path / "unused"),
                          "--tokenizer", str(tmp_path / "unused-tokenizer")])
    assert result == 0 and json.loads(capsys.readouterr().out)["worker"]["shutdown_verified"]
    assert json.loads((output / "fixture.json").read_text())["deadline_in_future"]
    assert output.with_name("run.worker.jsonl").exists()


@pytest.mark.parametrize("profile_name,samples", [("release", 4), ("repair_reliability", 2)])
def test_screen_summary_does_not_count_failed_full_reward_rows_as_solves(
        tmp_path, monkeypatch, capsys, profile_name, samples):
    monkeypatch.setenv("HF_TOKEN", "offline-fixture-placeholder")
    monkeypatch.setattr(screen.helper, "load_counter", lambda *a: screen.helper.TokenCounter())
    monkeypatch.setattr(screen, "quote", lambda *a: {"provider": {"pricing": {"input": .2, "output": 2.5}}})
    def failed_episode(task, seed, sample, *args):
        return {"task_id": task, "seed": seed, "sample": sample, "solved": True, "reward": 1,
                "failure": "invalid_json_action", "prompt_sha256": "a" * 64,
                "termination_grading": {"terminal_reward": 1, "counts_as_valid_completion": False}}
    monkeypatch.setattr(screen, "episode", failed_episode)
    profile = screen.get_profile(profile_name, "screen")
    profile["groups"] = [["software_repair-counts-d2", 1070300]]
    profile["signal_task_ids"] = ["software_repair-counts-d2"]
    output = tmp_path / "run"
    args = Namespace(output=output, budget_receipt=receipt(tmp_path), tokenizer=tmp_path / "unused",
                     stage="screen", profile=profile_name)
    assert screen._execute(time.monotonic() + 30, args, profile) == 0
    summary = json.loads((output / "complete.json").read_text())
    assert summary["rollouts"] == samples and summary["full_solves"] == 0
    assert summary["failed_episode_terminal_diagnostics"] == samples


@pytest.mark.parametrize("remaining,expected_timeout", [(200, 180), (45, 45)])
def test_provider_wait_can_exceed_old_limit_but_never_remaining_wall_budget(
        tmp_path, monkeypatch, remaining, expected_timeout):
    monkeypatch.setattr(screen, "_now", lambda: 100)
    frozen = {"provider": {"pricing": {"input": .2, "output": 2.5}}}
    monkeypatch.setattr(screen, "quote", lambda *a: frozen)
    observed = []
    def provider(opener, base, token, payload, timeout):
        observed.append(timeout)
        return {"id": "offline-timeout-fixture", "usage": {"prompt_tokens": 100, "completion_tokens": 10},
                "choices": [{"message": {"content": '{"op":"submit"}'}, "finish_reason": "stop"}]}
    monkeypatch.setattr(screen.helper, "provider_call", provider)
    screen.episode("software_repair-counts-d2", 1086001, 0, "offline-fixture-placeholder",
                   screen.helper.TokenCounter(), screen.DollarReservations(receipt(tmp_path)),
                   frozen, threading.Event(), 100 + remaining, "timeout-bound-fixture")
    assert observed == [expected_timeout]


@pytest.mark.parametrize("code", [429, 503])
def test_provider_http_status_is_preserved_without_error_body(tmp_path, monkeypatch, code):
    frozen = {"provider": {"pricing": {"input": .2, "output": 2.5}}}
    monkeypatch.setattr(screen, "quote", lambda *a: frozen)
    def fail(*args):
        raise urllib.error.HTTPError(screen.BASE, code, "private upstream detail", {}, None)
    monkeypatch.setattr(screen.helper, "provider_call", fail)
    result = screen.episode(
        "software_repair-counts-d2", 1090201, 0, "offline-fixture-placeholder",
        screen.helper.TokenCounter(), screen.DollarReservations(receipt(tmp_path)),
        frozen, threading.Event(), time.monotonic() + 30, "http-diagnostic-fixture",
    )
    assert result["failure"] == "provider_or_reservation_failure"
    assert result["failure_type"] == "HTTPError" and result["provider_http_status"] == code
    assert "private upstream detail" not in json.dumps(result)
