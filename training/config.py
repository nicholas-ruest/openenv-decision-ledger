"""Validated configuration and explicit readiness checks."""
from __future__ import annotations

import hashlib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SeedRange(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    start: int = Field(ge=0)
    count: int = Field(ge=1, le=100000)

    def seeds(self) -> range:
        return range(self.start, self.start + self.count)


class TrainingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    runtime_source_revision: str
    environment_source_sha256: str
    task_source_sha256: str
    model_path: str | None = None
    model_revision: str | None = None
    model_tree_sha256: str | None = None
    tokenizer_sha256: str | None = None
    task_ids: list[str]
    task_mix_confirmed: bool = False
    target_hardware_smoke_verified: bool = False
    train_seeds: SeedRange
    validation_seeds: SeedRange
    test_seeds: SeedRange
    num_generations: int = Field(default=4, ge=2, le=8)
    max_steps: int = Field(default=4, ge=2, le=16)
    max_completion_tokens: int = Field(default=8192, ge=16, le=8192)
    max_context_tokens: int = Field(default=16384, ge=128, le=16384)
    max_optimizer_steps: int = Field(default=100, ge=1, le=10000)
    max_wall_seconds: int = Field(default=3600, ge=60, le=14400)
    learning_rate: float = Field(default=0.000001, gt=0, le=0.001)
    temperature: float = Field(default=0.7, gt=0, le=2)
    thinking: bool = True

    @model_validator(mode="after")
    def check_splits(self) -> "TrainingConfig":
        intervals = [self.train_seeds, self.validation_seeds, self.test_seeds]
        for i, left in enumerate(intervals):
            for right in intervals[i + 1:]:
                if max(left.start, right.start) < min(
                    left.start + left.count, right.start + right.count
                ):
                    raise ValueError("Training, validation and test seeds overlap")
        if not self.task_ids or len(set(self.task_ids)) != len(self.task_ids):
            raise ValueError("Task IDs must be nonempty and unique")
        return self

    def blockers(self) -> list[str]:
        issues = []
        if not self.task_mix_confirmed:
            issues.append("task_mix_unconfirmed")
        if not self.target_hardware_smoke_verified:
            issues.append("target_gpu_smoke_unverified")
        if not all((self.model_path, self.model_revision,
                    self.model_tree_sha256, self.tokenizer_sha256)):
            issues.append("model_checkpoint_and_tokenizer_not_frozen")
        return issues


def verify_runtime(config: TrainingConfig, runtime_root: Path) -> None:
    """Reject runtime drift without changing any runtime files."""
    checks = {
        "environment.py": config.environment_source_sha256,
        "tasks.py": config.task_source_sha256,
    }
    for name, expected in checks.items():
        actual = hashlib.sha256((runtime_root / "arena_env" / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Pinned runtime file changed: {name}")


def checkpoint_tree_sha256(root: Path) -> str:
    """Bind the entire local checkpoint; credentials are never read."""
    files = sorted(p for p in root.rglob("*") if p.is_file())
    if not files or any(p.is_symlink() for p in files):
        raise ValueError("Checkpoint must contain regular local files")
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(root).as_posix()
        if "token" in path.name.lower() and path.name not in {
            "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json"
        }:
            raise ValueError("Unexpected token-like file in checkpoint")
        digest.update(relative.encode() + b"\0")
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()
