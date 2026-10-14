"""Bounded local worker and allowlisted artifact export. No provider API calls."""
from __future__ import annotations

import hashlib
import json
import math
import os
import signal
import subprocess
import tarfile
import time
from pathlib import Path


def compute_ceiling(hourly_usd: float, timeout_seconds: int, cap_usd: float) -> float:
    if (not math.isfinite(hourly_usd) or hourly_usd <= 0 or
            not math.isfinite(cap_usd) or cap_usd <= 0 or timeout_seconds <= 0):
        raise ValueError("Invalid compute quote")
    # HF Jobs bills per minute. Include two minutes for startup; a job-level
    # timeout is still mandatory because a local timeout cannot stop billing.
    cost = hourly_usd * (math.ceil(timeout_seconds / 60) + 2) / 60
    if cost > cap_usd:
        raise ValueError("Compute quote exceeds the approved phase cap")
    return cost


def bounded_worker(argv: list[str], *, cwd: Path, seconds: float, grace: float = 2) -> dict:
    if seconds <= 0 or grace <= 0:
        raise ValueError("Positive deadline required")
    started = time.monotonic()
    # No child environment/argv/log contents enter this report.
    process = subprocess.Popen(argv, cwd=cwd, start_new_session=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    expired = False
    try:
        process.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        expired = True
    finally:
        # Kill descendants even when the direct worker exited successfully.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
    return {"status": "deadline" if expired else "completed" if process.returncode == 0 else "failed",
            "returncode": process.returncode, "elapsed_seconds": time.monotonic() - started,
            "provider_billing_stopped": None,
            "limitation": "Local process cleanup only; provider job timeout must stop billing."}


ALLOWED = {"adapter_config.json", "adapter_model.safetensors", "config.json",
           "generation_config.json", "tokenizer.json", "tokenizer_config.json",
           "special_tokens_map.json", "vocab.json", "merges.txt", "added_tokens.json", "chat_template.jinja"}


def export_checkpoint(checkpoint: Path, archive: Path) -> dict:
    if checkpoint.is_symlink() or not checkpoint.is_dir():
        raise ValueError("Regular checkpoint directory required")
    entries = sorted(checkpoint.iterdir())
    # Trainer emits a pickle of its arguments and PEFT emits a model card.
    # Neither is necessary for reload; exclude both without reading them.
    excluded = {"training_args.bin", "README.md"}
    if not entries or any(p.is_symlink() or not p.is_file() or p.name not in ALLOWED | excluded for p in entries):
        raise ValueError("Checkpoint contains an unapproved artifact")
    files = [p for p in entries if p.name in ALLOWED]
    if not (checkpoint / "adapter_model.safetensors").is_file():
        raise ValueError("LoRA weights missing")
    if archive.exists() or archive.is_symlink():
        raise ValueError("New export path required")
    manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    temporary = archive.with_suffix(archive.suffix + ".partial")
    if temporary.exists():
        raise ValueError("Partial export already exists")
    try:
        with tarfile.open(temporary, "w:gz") as bundle:
            for p in files:
                bundle.add(p, arcname="checkpoint/" + p.name, recursive=False)
        temporary.rename(archive)
    finally:
        temporary.unlink(missing_ok=True)
    return {"files": manifest, "excluded_metadata": [p.name for p in entries if p.name in excluded],
            "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "export_scope": "local allowlisted LoRA checkpoint; no Hub upload"}
