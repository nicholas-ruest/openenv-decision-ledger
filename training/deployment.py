"""Offline HF Jobs configuration. This module cannot create a job."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from training.config import TrainingConfig, verify_runtime
from training.lifecycle import compute_ceiling


class Deployment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    namespace: str
    image: str
    model_source: str = "Qwen/Qwen3.8-27B"
    model_revision: str
    input_bucket: str
    input_path: str
    output_bucket: str
    run_id: str
    phase: str = "hardware_preflight"
    provider_timeout_seconds: int = Field(default=3480, ge=300, le=14400)
    session_seconds: int = Field(default=3000, ge=60, le=13800)
    hourly_usd: float = Field(default=5.0, gt=0)
    phase_cap_usd: float = Field(default=5.0, gt=0)
    image_published: bool = False
    input_snapshot_attested: bool = False
    output_bucket_attested: bool = False
    gpu_budget_approved: bool = False

    @model_validator(mode="after")
    def check_binding(self):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", self.namespace):
            raise ValueError("Explicit HF namespace required")
        if not re.fullmatch(r"[a-zA-Z0-9./_-]+@sha256:[0-9a-f]{64}", self.image):
            raise ValueError("Immutable container digest required")
        if not re.fullmatch(r"[0-9a-f]{40}", self.model_revision):
            raise ValueError("Immutable model revision required")
        for source in (self.model_source, self.input_bucket, self.output_bucket):
            if not re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+", source):
                raise ValueError("Explicit HF volume source required")
        if any(x.split("/")[0] != self.namespace for x in (self.input_bucket, self.output_bucket)):
            raise ValueError("Buckets must belong to the explicit namespace")
        for path in (self.input_path, self.run_id):
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", path):
                raise ValueError("Safe exclusive run and input identifiers required")
        if self.phase not in {"hardware_preflight", "pilot"}:
            raise ValueError("Unknown focused phase")
        if self.session_seconds + 300 > self.provider_timeout_seconds:
            raise ValueError("Reserve at least five minutes for load/export/cleanup")
        compute_ceiling(self.hourly_usd, self.provider_timeout_seconds, self.phase_cap_usd)
        return self


def deployment_preview(spec: Deployment, config: TrainingConfig):
    """Return SDK-compatible arguments, not a POST body or runnable authorization."""
    if config.task_ids != ["software_change-d2"]:
        raise ValueError("Single software category required")
    if spec.model_revision != config.model_revision:
        raise ValueError("Deployment model revision differs from training pin")
    if config.max_wall_seconds != spec.session_seconds:
        raise ValueError("Session and deployment deadlines differ")
    blockers = [name for name, attested in {
        "published_image_unverified": spec.image_published,
        "input_snapshot_unverified": spec.input_snapshot_attested,
        "output_bucket_unverified": spec.output_bucket_attested,
        "gpu_budget_unapproved": spec.gpu_budget_approved,
    }.items() if not attested]
    if not all((config.model_tree_sha256, config.tokenizer_sha256)):
        blockers.append("checkpoint_tree_not_frozen")
    if spec.phase == "pilot":
        blockers.extend(config.blockers())
    blockers.append("paid_cli_locked")
    # Explicit SDK Volume fields; no implicit main revision or local-directory sync.
    volumes = [
        {"type": "model", "source": spec.model_source, "revision": spec.model_revision,
         "mount_path": "/model", "read_only": True},
        {"type": "bucket", "source": spec.input_bucket, "path": spec.input_path,
         "mount_path": "/inputs", "read_only": True},
        {"type": "bucket", "source": spec.output_bucket,
         "mount_path": "/artifacts", "read_only": False},
    ]
    command = ["python", "-m", "training.session", "--execute",
               "--config", "/inputs/training-config.json", "--runtime-root",
               "/app/integrations/openenv-arena", "--model-root", "/model",
               "--output", f"/tmp/{spec.run_id}", "--artifact-root", "/artifacts",
               "--phase", spec.phase]
    return {"sdk_arguments": {"namespace": spec.namespace, "image": spec.image,
        "command": command, "flavor": "h200", "timeout": spec.provider_timeout_seconds,
        "attempts": 1, "volumes": volumes, "ssh": False, "expose": [], "expose_public": [],
        "env": {"HF_HUB_OFFLINE": "1", "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1"}},
        "execution_enabled": False, "created": False, "blockers": sorted(set(blockers)),
        "compute_allowance_usd": compute_ceiling(spec.hourly_usd,
             spec.provider_timeout_seconds, spec.phase_cap_usd),
        "compute_allowance_is_account_cap": False,
        "limitations": ["Storage, taxes and provider billing require separate verification",
            "Five-minute reserve is advisory; provider timeout bounds the entire job",
            "Checkpoint retrieval and mount durability require a measured hardware preflight",
            "No token is passed to the container; volume access depends on job namespace permissions"]}


def validate_session_inputs(config, runtime_root, model_root, artifact_root):
    """CPU-only input binding; does not import Torch or load weights."""
    from training.config import checkpoint_tree_sha256
    import hashlib
    verify_runtime(config, runtime_root)
    for path in (model_root, artifact_root):
        if path.is_symlink() or not path.is_dir():
            raise ValueError("Existing regular mounted roots required")
    if config.model_path != str(model_root):
        raise ValueError("Configuration model path differs from mounted root")
    if not config.model_tree_sha256 or checkpoint_tree_sha256(model_root) != config.model_tree_sha256:
        raise ValueError("Frozen checkpoint hash differs")
    if hashlib.sha256((model_root / "tokenizer.json").read_bytes()).hexdigest() != config.tokenizer_sha256:
        raise ValueError("Frozen tokenizer hash differs")
    return {"runtime_verified": True, "checkpoint_tree_verified": True,
        "tokenizer_verified": True, "mount_exists": True,
        "remote_durability_verified": False, "model_loaded": False}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--deployment", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, required=True)
    args = parser.parse_args(argv)
    config = TrainingConfig.model_validate_json(args.config.read_text())
    verify_runtime(config, args.runtime_root)
    spec = Deployment.model_validate_json(args.deployment.read_text())
    print(json.dumps(deployment_preview(spec, config), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
