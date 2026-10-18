"""Publish an allowlisted checkpoint to an existing mounted output volume.

This never creates remote storage, uploads through credentials, or claims that
a local test directory is provider-persistent. A mount must be independently
configured and verified before any paid job.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re


def publish_archive(archive, root, run_id, *, volume_attested=False):
    archive, root = Path(archive), Path(root)
    if not volume_attested:
        raise ValueError("Durable output volume not independently attested")
    if not root.is_dir() or root.is_symlink() or not archive.is_file() or archive.is_symlink():
        raise ValueError("Existing regular output root and archive required")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", run_id):
        raise ValueError("Safe unique run ID required")
    destination = root / run_id
    destination.mkdir(exist_ok=False)
    # Exclusive creation: never overwrite previous runs, even on failure.
    temporary = destination / "checkpoint.tar.gz.partial"
    digest = hashlib.sha256()
    with archive.open("rb") as source, temporary.open("xb") as sink:
        while block := source.read(1024 * 1024):
            digest.update(block)
            sink.write(block)
        sink.flush()
        os.fsync(sink.fileno())
    copied = hashlib.sha256(temporary.read_bytes()).hexdigest()
    if copied != digest.hexdigest():
        raise ValueError("Artifact copy verification failed")
    final = destination / "checkpoint.tar.gz"
    temporary.rename(final)
    receipt = {"archive_sha256": copied, "archive_bytes": final.stat().st_size,
               "run_id": run_id, "copy_verified": True,
               "durable_volume_attested_by_caller": True,
               "limitation": "Local copy/hash/fsync verification; provider persistence must be attested separately."}
    try:
        fd = os.open(destination, os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        # Some managed mounts do not implement directory fsync; do not promote
        # this to a guarantee of provider durability.
        receipt["directory_fsync_supported"] = False
    else:
        receipt["directory_fsync_supported"] = True
    with (destination / "receipt.json").open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    # Flush both the receipt directory and its new entry in the existing root.
    for directory in (destination, root):
        try:
            fd = os.open(directory, os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError:
            # The earlier receipt explicitly states the scope of this check;
            # a provider-mounted filesystem still needs independent validation.
            raise OSError("Output directory flush failed; durable publish unconfirmed") from None
    return receipt
