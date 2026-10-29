"""HF Jobs request preview and watchdog; no job-creation operation exists here."""
from __future__ import annotations

import re
import time

from training.lifecycle import compute_ceiling

TERMINAL = {"COMPLETED", "CANCELED", "ERROR", "DELETED"}


def request_preview(image, hourly_usd, timeout_seconds, phase_cap_usd):
    if not re.fullmatch(r"[a-zA-Z0-9./_-]+@sha256:[0-9a-f]{64}", image):
        raise ValueError("Pinned public image digest required")
    estimate = compute_ceiling(hourly_usd, timeout_seconds, phase_cap_usd)
    return {"request": {"image": image, "flavor": "h200", "timeout": timeout_seconds,
        "attempts": 1, "expose": [], "expose_public": [], "ssh": False,
        "command": ["python", "-m", "training.session", "--execute"],
        "env": {"HF_HUB_OFFLINE": "1", "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1"}},
        "planned_compute_usd_including_two_startup_minutes": estimate,
        "created": False, "execution_enabled": False,
        "unresolved": ["Target CLI remains deliberately locked", "CUDA image must be built and validated",
            "Frozen local checkpoint/input volume and durable output volume not attached",
            "Price recheck, explicit GPU budget, account permissions and storage quote required",
            "Two-minute startup allowance is an estimate, not an account billing cap"]}


def monitor_existing(provider, job_id, *, seconds, cancel_grace=30,
                     clock=time.monotonic, pause=time.sleep, interval=5):
    """Poll a previously approved job. Cancellation must be observed, not assumed."""
    if seconds <= 0 or cancel_grace <= 0 or not 0 < interval <= 30:
        raise ValueError("Bounded monitor timings required")
    deadline = clock() + seconds
    canceled, error = False, None
    stage = "UNKNOWN"
    while True:
        try:
            status = provider.inspect_job(job_id=job_id).status.stage
            stage = getattr(status, "value", status)
        except Exception as exc:
            error = type(exc).__name__
        if stage in TERMINAL:
            return {"terminal_stage": stage, "cancel_requested": canceled,
                    "terminal_verified": True, "provider_error_type": error,
                    "limitation": "Observed terminal state; invoice not independently reconciled"}
        if clock() >= deadline or error:
            break
        pause(min(interval, max(0, deadline - clock())))
    try:
        provider.cancel_job(job_id=job_id)
        canceled = True
    except Exception as exc:
        error = type(exc).__name__
    until = clock() + cancel_grace
    while clock() < until:
        try:
            status = provider.inspect_job(job_id=job_id).status.stage
            stage = getattr(status, "value", status)
        except Exception as exc:
            error = type(exc).__name__
        if stage in TERMINAL:
            return {"terminal_stage": stage, "cancel_requested": canceled,
                    "terminal_verified": True, "provider_error_type": error,
                    "limitation": "Observed terminal state; invoice not independently reconciled"}
        pause(min(interval, max(0, until - clock())))
    return {"terminal_stage": stage, "cancel_requested": canceled,
            "terminal_verified": False, "provider_error_type": error,
            "limitation": "Stop could not be verified; provider timeout remains the backstop"}
