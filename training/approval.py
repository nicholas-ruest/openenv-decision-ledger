"""A job-specific approval capability, issued only after explicit GPU budget approval.

No real capability is issued by repository code or during preparation. The
operator supplies a separate random environment key after the user approves;
it is never the HF credential, and never part of argv or an exported artifact.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import re
import time

KEY_ENV = "OPENENV_PREFLIGHT_APPROVAL_KEY"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def approval_key():
    value = os.environ.get(KEY_ENV, "")
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise PermissionError("Paid execution locked: approval capability unavailable")
    if value == os.environ.get("HF_TOKEN"):
        raise PermissionError("HF credential cannot authorize a training worker")
    return bytes.fromhex(value)


def verify_approval(envelope, spec, config, *, now=None):
    key = approval_key()  # Fails before provider contact or model import.
    if not isinstance(envelope, dict) or set(envelope) != {"claims", "signature"}:
        raise PermissionError("Paid execution locked: malformed approval")
    claims = envelope["claims"]
    if not isinstance(claims, dict) or set(claims) != {
        "request_sha256", "config_sha256", "run_id", "phase", "expires_at", "max_compute_usd"
    }:
        raise PermissionError("Paid execution locked: invalid approval claims")
    signature = hmac.new(key, canonical(claims), hashlib.sha256).hexdigest()
    supplied = envelope.get("signature")
    if not isinstance(supplied, str) or not hmac.compare_digest(signature, supplied):
        raise PermissionError("Paid execution locked: approval signature differs")
    now = time.time() if now is None else now
    expiry, cap = claims["expires_at"], claims["max_compute_usd"]
    if (type(expiry) not in (int, float) or not math.isfinite(expiry) or
            not now < expiry <= now + 7200 or type(cap) not in (int, float) or
            not math.isfinite(cap) or cap <= 0):
        raise PermissionError("Paid execution locked: approval expired or invalid")
    if (spec.phase != "hardware_preflight" or claims["phase"] != spec.phase or
            claims["run_id"] != spec.run_id or not spec.gpu_budget_approved or
            claims["request_sha256"] != digest(spec.model_dump()) or
            claims["config_sha256"] != digest(config.model_dump())):
        raise PermissionError("Paid execution locked: request/configuration differs")
    from training.lifecycle import compute_ceiling
    estimate = compute_ceiling(spec.hourly_usd, spec.provider_timeout_seconds, spec.phase_cap_usd)
    if estimate > cap:
        raise PermissionError("Paid execution locked: compute allowance exceeded")
    if not (spec.image_published and spec.input_snapshot_attested and spec.output_bucket_attested):
        raise PermissionError("Paid execution locked: deployment inputs unverified")
    return {"run_id": spec.run_id, "phase": spec.phase, "compute_allowance_usd": estimate}
