"""Real target entrypoint with signed, job-specific approval. Default is locked."""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

from training.approval import approval_key, verify_approval
from training.config import TrainingConfig
from training.deployment import Deployment, validate_session_inputs


def run_bound_worker(spec, config, envelope, *, runtime_root, model_root,
                     artifact_root, output, input_validator=None, session_runner=None):
    verify_approval(envelope, spec, config)
    if str(model_root) != "/model" and input_validator is None:
        raise ValueError("Pinned model mount required")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", spec.run_id):
        raise ValueError("Exclusive safe run identifier required")
    if output.name != spec.run_id or output.exists() or output.is_symlink():
        raise ValueError("New approved output directory required")
    if spec.session_seconds != config.max_wall_seconds or config.task_ids != ["software_change-d2"]:
        raise ValueError("Bounded software-only session required")
    validator = input_validator or validate_session_inputs
    validator(config, runtime_root, model_root, artifact_root)
    # A new report is reserved before loading weights. It is both a replay guard
    # and a small write/read probe of the requested output mount.
    reports = artifact_root / "preflight-reports"
    reports.mkdir(exist_ok=True)
    if reports.is_symlink():
        raise ValueError("Regular output reports directory required")
    report_path = reports / (spec.run_id + ".json")
    initial = {"status": "starting", "run_id": spec.run_id,
               "job_id": os.environ.get("JOB_ID"), "gpu_fit_verified": False}
    with report_path.open("x") as stream:
        json.dump(initial, stream)
        stream.flush()
        os.fsync(stream.fileno())
    if json.loads(report_path.read_text()) != initial:
        raise ValueError("Output mount write/read differs")
    if session_runner is None:
        from training.session import run_session
        session_runner = run_session
    try:
        result = session_runner(config, runtime_root, output, phase="hardware_preflight",
                                artifact_root=artifact_root, volume_attested=True)
        report = {"status": result["status"], "run_id": spec.run_id,
                  "session": result, "provider_billing_stopped": None}
    except Exception as exc:
        report = {"status": "failed", "run_id": spec.run_id,
                  "error_type": type(exc).__name__, "gpu_fit_verified": False,
                  "provider_billing_stopped": None}
    temporary = report_path.with_suffix(".final")
    with temporary.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(report_path)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", required=True)
    parser.add_argument("--deployment", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    args = parser.parse_args(argv)
    approval_key()  # Preparation and legacy --execute remain locked without a key.
    spec = Deployment.model_validate_json(args.deployment.read_text())
    config = TrainingConfig.model_validate_json(args.config.read_text())
    report = run_bound_worker(spec, config, json.loads(args.approval.read_text()),
        runtime_root=Path("/app/integrations/openenv-arena"), model_root=Path("/model"),
        artifact_root=Path("/artifacts"), output=Path("/tmp") / spec.run_id)
    return 0 if report["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
