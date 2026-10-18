"""Verify mounted weights against preapproved file hashes, without Hub login."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


def verify_manifest(root: Path, manifest_path: Path, manifest_sha256: str, revision: str):
    if root.is_symlink() or not root.is_dir() or manifest_path.is_symlink():
        raise ValueError("Regular checkpoint root and manifest required")
    raw = manifest_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest_sha256:
        raise ValueError("Checkpoint manifest changed")
    manifest = json.loads(raw)
    if manifest.get("revision") != revision or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Checkpoint manifest revision differs")
    files = manifest.get("files", {})
    required = {"config.json", "tokenizer.json", "tokenizer_config.json", "model.safetensors.index.json"}
    if not required.issubset(files):
        raise ValueError("Checkpoint manifest is incomplete")
    # Root loadable files must all be pinned; a rogue single-file checkpoint can
    # otherwise take precedence over the pinned sharded index.
    for path in root.iterdir():
        if path.is_symlink():
            raise ValueError("Checkpoint symlink rejected")
        if path.is_file() and path.name not in files:
            raise ValueError("Unpinned checkpoint root file")
    for name, expected in files.items():
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name) or name in {".", ".."}:
            raise ValueError("Unsafe manifest file path")
        if not re.fullmatch(r"[0-9a-f]{64}", expected.get("sha256", "")):
            raise ValueError("Invalid manifest file digest")
        path = root / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size != expected.get("size"):
            raise ValueError("Mounted checkpoint file differs")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != expected["sha256"]:
            raise ValueError("Mounted checkpoint file hash differs")
    index = json.loads((root / "model.safetensors.index.json").read_text())
    shards = set(index.get("weight_map", {}).values())
    if not shards or not shards.issubset(files) or any(not x.endswith(".safetensors") for x in shards):
        raise ValueError("Weight index refers to unpinned shards")
    return {"manifest_sha256": manifest_sha256, "files_verified": len(files),
            "weight_shards_verified": len(shards), "model_loaded": False}


def verify_checkpoint(config, root):
    from training.config import checkpoint_tree_sha256
    if config.model_tree_sha256:
        if checkpoint_tree_sha256(root) != config.model_tree_sha256:
            raise ValueError("Frozen checkpoint hash differs")
        return {"verification": "full_tree_sha256", "model_loaded": False}
    if config.model_manifest_path and config.model_manifest_sha256:
        return verify_manifest(root, Path(config.model_manifest_path),
                               config.model_manifest_sha256, config.model_revision)
    raise ValueError("Frozen checkpoint hashes required")
