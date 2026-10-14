import json
import os
import sys
import tarfile
import time
from pathlib import Path

import pytest

from training.lifecycle import bounded_worker, compute_ceiling, export_checkpoint


def test_quote_is_minute_rounded_and_includes_startup():
    assert compute_ceiling(5.0, 61, 1.0) == pytest.approx(5.0 * 4 / 60)
    with pytest.raises(ValueError, match="exceeds"):
        compute_ceiling(5.0, 3600, 5.0)
    with pytest.raises(ValueError):
        compute_ceiling(float("nan"), 3600, 10)


def test_failed_worker_retains_checkpoint_and_exit_status(tmp_path):
    code = "from pathlib import Path; Path('recovery').write_text('saved'); raise SystemExit(3)"
    result = bounded_worker([sys.executable, "-c", code], cwd=tmp_path, seconds=3)
    assert result["status"] == "failed" and result["returncode"] == 3
    assert (tmp_path / "recovery").read_text() == "saved"
    assert result["provider_billing_stopped"] is None


def test_deadline_kills_forked_descendant_without_losing_artifact(tmp_path):
    code = "import os,time; from pathlib import Path; p=os.fork(); Path('child').write_text(str(p)) if p else None; Path('recovery').write_text('saved'); time.sleep(20)"
    result = bounded_worker([sys.executable, "-c", code], cwd=tmp_path, seconds=0.3, grace=0.1)
    assert result["status"] == "deadline"
    assert (tmp_path / "recovery").exists()
    pid = int((tmp_path / "child").read_text())
    stat = Path(f"/proc/{pid}/stat")
    assert not stat.exists() or stat.read_text().split()[2] == "Z"


def test_export_contains_only_checkpoint_and_rejects_extra_or_symlink(tmp_path):
    checkpoint = tmp_path / "checkpoint"
    checkpoint.mkdir()
    (checkpoint / "adapter_model.safetensors").write_bytes(b"fixture")
    (checkpoint / "training_args.bin").write_bytes(b"excluded fixture metadata")
    result = export_checkpoint(checkpoint, tmp_path / "export.tar.gz")
    with tarfile.open(tmp_path / "export.tar.gz") as bundle:
        assert bundle.getnames() == ["checkpoint/adapter_model.safetensors"]
    assert len(result["archive_sha256"]) == 64
    assert result["excluded_metadata"] == ["training_args.bin"]
    (checkpoint / "credential.env").write_text("fixture")
    with pytest.raises(ValueError, match="unapproved"):
        export_checkpoint(checkpoint, tmp_path / "other.tar.gz")
    (checkpoint / "credential.env").unlink()
    (checkpoint / "config.json").symlink_to(tmp_path / "export.tar.gz")
    with pytest.raises(ValueError, match="unapproved"):
        export_checkpoint(checkpoint, tmp_path / "third.tar.gz")
