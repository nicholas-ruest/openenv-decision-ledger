from types import SimpleNamespace

import pytest

from training.job_control import monitor_existing, request_preview


class FakeClock:
    value = 0
    def now(self):
        return self.value
    def advance(self, seconds):
        self.value += seconds


class Provider:
    def __init__(self, states, cancellation_works=True):
        self.states, self.cancel_calls = iter(states), 0
        self.stage, self.cancellation_works = "RUNNING", cancellation_works
    def inspect_job(self, *, job_id):
        self.stage = next(self.states, self.stage)
        return SimpleNamespace(status=SimpleNamespace(stage=self.stage))
    def cancel_job(self, *, job_id):
        self.cancel_calls += 1
        if self.cancellation_works:
            self.stage = "CANCELED"


def test_preview_has_provider_timeout_no_retry_and_no_credentials():
    plan = request_preview("ghcr.io/example/worker@sha256:" + "a" * 64, 5, 3480, 5)
    assert plan["request"]["timeout"] == 3480
    assert plan["request"]["attempts"] == 1
    assert plan["created"] is False and "secrets" not in plan["request"]
    with pytest.raises(ValueError, match="digest"):
        request_preview("latest", 5, 60, 5)


@pytest.mark.parametrize("stage", ["COMPLETED", "ERROR", "DELETED"])
def test_terminal_job_needs_no_cancellation(stage):
    clock, provider = FakeClock(), Provider([stage])
    result = monitor_existing(provider, "fixture", seconds=10, clock=clock.now, pause=clock.advance)
    assert result["terminal_verified"] and result["terminal_stage"] == stage
    assert provider.cancel_calls == 0


@pytest.mark.parametrize("works", [True, False])
def test_deadline_requires_observed_terminal_state(works):
    clock, provider = FakeClock(), Provider(["RUNNING"], works)
    result = monitor_existing(provider, "fixture", seconds=10, cancel_grace=10,
                              clock=clock.now, pause=clock.advance)
    assert provider.cancel_calls == 1
    assert result["terminal_verified"] is works
