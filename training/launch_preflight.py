"""One approved hardware preflight, with an exclusive local launch journal.

No retries: an ambiguous creation response requires manual Jobs reconciliation.
No approval capability is issued here. Legacy pilot execution stays locked.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from training.approval import KEY_ENV, approval_key, verify_approval
from training.config import TrainingConfig
from training.deployment import Deployment, deployment_preview
from training.job_control import monitor_existing
from training.provider_http import BoundedJobsApi


def approved_payload(spec, config, envelope):
    verify_approval(envelope, spec, config)
    preview = deployment_preview(spec, config)["sdk_arguments"]
    volumes = [{("mountPath" if k == "mount_path" else "readOnly" if k == "read_only" else k): v
                for k, v in volume.items()} for volume in preview["volumes"]]
    return {"command": ["python", "-m", "training.hardware_preflight", "--execute",
        "--deployment", "/inputs/deployment.json", "--config", "/inputs/training-config.json",
        "--approval", "/inputs/approval.json"], "arguments": [],
        "environment": preview["env"], "flavor": "h200", "attempts": 1,
        "timeoutSeconds": spec.provider_timeout_seconds,
        "labels": {"openenv_run_id": spec.run_id}, "volumes": volumes,
        "dockerImage": spec.image,
        # Separate run-specific capability, never the HF credential.
        "secrets": {KEY_ENV: approval_key().hex()}}


def launch_once(spec, config, envelope, journal_root, *, provider=None, monitor=None):
    payload = approved_payload(spec, config, envelope)  # Before directory/network access.
    root = Path(journal_root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Existing private journal directory required")
    path = root / (spec.run_id + ".json")
    state = {"run_id": spec.run_id, "status": "creation_unknown", "job_id": None,
             "terminal_verified": False}
    # Exclusive claim precedes POST. Never remove it, even after timeout.
    with path.open("x") as stream:
        json.dump(state, stream)
        stream.flush()
        os.fsync(stream.fileno())
    def save():
        temporary = path.with_suffix(".next")
        with temporary.open("x") as stream:
            json.dump(state, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    provider = provider or BoundedJobsApi(spec.namespace, allow_creation=True, allow_cancellation=True)
    if getattr(provider, "namespace", spec.namespace) != spec.namespace:
        raise ValueError("Provider namespace differs")
    started = time.monotonic()
    try:
        state["job_id"] = provider.create_job(payload)
    except Exception as exc:
        state["error_type"] = type(exc).__name__
        save()
        return state  # No retry or guessed cancellation; provider timeout is backstop.
    state["status"] = "created"
    save()  # Persist ID before monitoring so a stopped controller is recoverable.
    watcher = monitor or monitor_existing
    try:
        outcome = watcher(provider, state["job_id"],
            seconds=max(1, spec.provider_timeout_seconds - (time.monotonic() - started)))
        state.update(outcome)
        state["status"] = "terminal" if outcome["terminal_verified"] else "stop_unverified"
    except Exception as exc:
        state.update(status="stop_unverified", error_type=type(exc).__name__)
        try:
            provider.cancel_job(job_id=state["job_id"])
        except Exception:
            pass
    save()
    return state


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", required=True)
    parser.add_argument("--deployment", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--journal-root", type=Path, required=True)
    args = parser.parse_args(argv)
    approval_key()  # Fail before opening files without explicit run capability.
    spec = Deployment.model_validate_json(args.deployment.read_text())
    config = TrainingConfig.model_validate_json(args.config.read_text())
    result = launch_once(spec, config, json.loads(args.approval.read_text()), args.journal_root)
    print(json.dumps(result, indent=2))  # State only, never request/secrets.
    return 0 if result["terminal_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
