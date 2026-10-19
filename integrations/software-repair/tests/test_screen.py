import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import threading
import time

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
