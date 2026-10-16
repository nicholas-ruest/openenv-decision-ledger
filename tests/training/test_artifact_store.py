import hashlib
import json

import pytest

from training.artifact_store import publish_archive


def test_verified_copy_exclusive_run_and_attestation_required(tmp_path):
    archive = tmp_path / "source.tar.gz"
    archive.write_bytes(b"archive fixture")
    root = tmp_path / "volume"
    root.mkdir()
    with pytest.raises(ValueError, match="attested"):
        publish_archive(archive, root, "run1")
    report = publish_archive(archive, root, "run1", volume_attested=True)
    assert report["copy_verified"]
    assert report["archive_sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert (root / "run1/receipt.json").is_file()
    assert json.loads((root / "run1/receipt.json").read_text()) == report
    with pytest.raises(FileExistsError):
        publish_archive(archive, root, "run1", volume_attested=True)
    with pytest.raises(ValueError):
        publish_archive(archive, root, "../escape", volume_attested=True)


def test_symlinked_source_is_rejected(tmp_path):
    source = tmp_path / "source"
    source.write_text("fixture")
    link = tmp_path / "link"
    link.symlink_to(source)
    with pytest.raises(ValueError):
        publish_archive(link, tmp_path, "run", volume_attested=True)
