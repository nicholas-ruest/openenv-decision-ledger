import asyncio
import json
import time

import httpx
import pytest

from training.provider_http import BoundedJobsApi

JOB = "a" * 24


def test_exact_namespace_paths_env_only_and_explicit_cancel(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "offline-fixture")
    calls = []
    def handler(request):
        calls.append((request.method, request.url.path))
        assert request.headers["Authorization"] == "Bearer offline-fixture"
        return httpx.Response(200, json={"status": {"stage": "RUNNING"}})
    api = BoundedJobsApi("fixture", transport=httpx.MockTransport(handler), allow_cancellation=True)
    assert api.inspect_job(job_id=JOB).status.stage == "RUNNING"
    api.cancel_job(job_id=JOB)
    assert calls == [("GET", f"/api/jobs/fixture/{JOB}"), ("POST", f"/api/jobs/fixture/{JOB}/cancel")]


def test_total_http_deadline_cancels_stalled_transport(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "offline-fixture")
    closed = []
    async def handler(request):
        try:
            await asyncio.sleep(20)
        finally:
            closed.append(True)
    api = BoundedJobsApi("fixture", request_seconds=0.05, transport=httpx.MockTransport(handler))
    started = time.monotonic()
    with pytest.raises(TimeoutError, match="deadline"):
        api.inspect_job(job_id=JOB)
    assert time.monotonic() - started < 2 and closed == [True]


@pytest.mark.parametrize("response", [
    httpx.Response(302, headers={"Location": "https://example.com"}),
    httpx.Response(200, content=b"x" * 65537),
    httpx.Response(500, text="untrusted response body"),
])
def test_redirect_oversize_and_provider_error_fail_closed(monkeypatch, response):
    monkeypatch.setenv("HF_TOKEN", "offline-fixture")
    api = BoundedJobsApi("fixture", transport=httpx.MockTransport(lambda _: response))
    with pytest.raises(RuntimeError, match="Bounded"):
        api.inspect_job(job_id=JOB)


def test_cancel_is_disabled_and_invalid_identity_never_requests():
    api = BoundedJobsApi("fixture")
    with pytest.raises(PermissionError):
        api.cancel_job(job_id=JOB)
    with pytest.raises(ValueError):
        api.inspect_job(job_id="../other")
    with pytest.raises(ValueError):
        BoundedJobsApi("../other")
