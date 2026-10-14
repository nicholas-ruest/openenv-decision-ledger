"""Bounded environment-only HF Jobs inspection/cancellation; never creates jobs."""
from __future__ import annotations

import asyncio
import json
import math
import os
import re
from types import SimpleNamespace


class BoundedJobsApi:
    def __init__(self, namespace, *, request_seconds=10.0, transport=None,
                 allow_cancellation=False):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", namespace):
            raise ValueError("Explicit verified namespace required")
        if not math.isfinite(request_seconds) or not 0 < request_seconds <= 15:
            raise ValueError("Request deadline must be within15 seconds")
        self.namespace = namespace
        self.request_seconds = request_seconds
        self.transport = transport
        self.allow_cancellation = allow_cancellation

    def _request(self, method, job_id, suffix=""):
        if not re.fullmatch(r"[0-9a-f]{24}", job_id):
            raise ValueError("Exact HF job ID required")
        credential = os.environ.get("HF_TOKEN")
        if not credential:
            raise ValueError("Private environment credential unavailable")

        async def bounded():
            import httpx
            # No auto-whoami, redirects, environment proxy or token-file lookup.
            async with httpx.AsyncClient(transport=self.transport,
                    timeout=self.request_seconds, follow_redirects=False,
                    trust_env=False) as client:
                url = f"https://huggingface.co/api/jobs/{self.namespace}/{job_id}{suffix}"
                async with client.stream(method, url, headers={
                        "Authorization": "Bearer " + credential}) as response:
                    if not 200 <= response.status_code < 300:
                        raise RuntimeError("Provider request rejected")
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > 65536:
                            raise RuntimeError("Provider response exceeds bound")
                    return json.loads(body) if body else {}

        async def total_deadline():
            return await asyncio.wait_for(bounded(), timeout=self.request_seconds)
        try:
            return asyncio.run(total_deadline())
        except TimeoutError:
            raise TimeoutError("Provider request deadline reached") from None
        except Exception:
            # Do not propagate response bodies, requests, credentials or errors.
            raise RuntimeError("Bounded provider request failed") from None

    def inspect_job(self, *, job_id):
        data = self._request("GET", job_id)
        stage = data.get("status", {}).get("stage")
        if stage not in {"COMPLETED", "CANCELED", "ERROR", "DELETED",
                         "RUNNING", "STARTING", "SCHEDULING", "QUEUED"}:
            raise ValueError("Unknown provider job stage")
        return SimpleNamespace(status=SimpleNamespace(stage=stage))

    def cancel_job(self, *, job_id):
        if not self.allow_cancellation:
            raise PermissionError("Cancellation capability not enabled")
        self._request("POST", job_id, "/cancel")
