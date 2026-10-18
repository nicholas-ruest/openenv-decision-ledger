"""Bounded environment-only HF Jobs HTTP; mutation capabilities default off."""
from __future__ import annotations

import asyncio
import json
import math
import os
import re
from types import SimpleNamespace


class BoundedJobsApi:
    def __init__(self, namespace, *, request_seconds=10.0, transport=None,
                 allow_cancellation=False, allow_creation=False):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", namespace):
            raise ValueError("Explicit verified namespace required")
        if not math.isfinite(request_seconds) or not 0 < request_seconds <= 15:
            raise ValueError("Request deadline must be within15 seconds")
        self.namespace = namespace
        self.request_seconds = request_seconds
        self.transport = transport
        self.allow_cancellation = allow_cancellation
        self.allow_creation = allow_creation

    def _request(self, method, job_id, suffix="", payload=None):
        if job_id is not None and not re.fullmatch(r"[0-9a-f]{24}", job_id):
            raise ValueError("Exact HF job ID required")
        if job_id is None and not (method == "POST" and self.allow_creation and payload is not None):
            raise PermissionError("Creation capability not enabled")
        credential = os.environ.get("HF_TOKEN")
        if not credential:
            raise ValueError("Private environment credential unavailable")

        async def bounded():
            import httpx
            # No auto-whoami, redirects, environment proxy or token-file lookup.
            async with httpx.AsyncClient(transport=self.transport,
                    timeout=self.request_seconds, follow_redirects=False,
                    trust_env=False) as client:
                url = f"https://huggingface.co/api/jobs/{self.namespace}"
                if job_id is not None:
                    url += f"/{job_id}{suffix}"
                async with client.stream(method, url, headers={
                        "Authorization": "Bearer " + credential}, json=payload) as response:
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

    def create_job(self, payload):
        if not self.allow_creation:
            raise PermissionError("Creation capability not enabled")
        data = self._request("POST", None, payload=payload)
        job_id = data.get("id")
        if not isinstance(job_id, str) or not re.fullmatch(r"[0-9a-f]{24}", job_id):
            raise RuntimeError("Creation result ambiguous; reconcile before any further launch")
        return job_id

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
