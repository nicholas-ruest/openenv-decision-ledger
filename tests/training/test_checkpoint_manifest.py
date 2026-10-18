import hashlib
import json

import pytest

from training.checkpoint_manifest import verify_manifest


def fixture(tmp_path):
    root = tmp_path / "weights"
    root.mkdir()
    contents = {"config.json": b"{}", "tokenizer.json": b"{}", "tokenizer_config.json": b"{}",
                "model.safetensors.index.json": json.dumps({"weight_map": {"fixture": "model-1.safetensors"}}).encode(),
                "model-1.safetensors": b"small-fake-weight-fixture"}
    for name, body in contents.items():
        (root / name).write_bytes(body)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"revision": "a" * 40, "files": {
        name: {"size": len(body), "sha256": hashlib.sha256(body).hexdigest()}
        for name, body in contents.items()}}))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return root, path, digest


def test_immutable_manifest_checks_all_shards_without_model_load(tmp_path):
    result = verify_manifest(*fixture(tmp_path), "a" * 40)
    assert result["files_verified"] == 5 and result["weight_shards_verified"] == 1
    assert not result["model_loaded"]


@pytest.mark.parametrize("change", ["weight", "extra", "manifest", "symlink", "revision"])
def test_preapproved_manifest_rejects_drift_and_checkpoint_precedence(tmp_path, change):
    root, path, digest = fixture(tmp_path)
    revision = "a" * 40
    if change == "weight":
        (root / "model-1.safetensors").write_bytes(b"wrong")
    elif change == "extra":
        (root / "model.safetensors").write_bytes(b"rogue-preferred-checkpoint")
    elif change == "manifest":
        path.write_text("changed")
    elif change == "symlink":
        (root / "config.json").unlink()
        (root / "config.json").symlink_to(path)
    else:
        revision = "b" * 40
    with pytest.raises(ValueError):
        verify_manifest(root, path, digest, revision)
