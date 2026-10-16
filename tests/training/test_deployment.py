import hashlib
import json
from pathlib import Path

import pytest
from huggingface_hub import Volume

from training.config import TrainingConfig, checkpoint_tree_sha256
from training.deployment import Deployment, deployment_preview, validate_session_inputs
from training.session import main


def config():
    return TrainingConfig.model_validate_json(
        Path("config/private-training-preparation.json").read_text()).model_copy(
            update={"max_wall_seconds": 3000})


def spec(**updates):
    data = dict(namespace="fixture", image="ghcr.io/fixture/worker@sha256:" + "a" * 64,
        model_revision=config().model_revision, input_bucket="fixture/input",
        output_bucket="fixture/output", input_path="frozen-configuration", run_id="hardware-1")
    data.update(updates)
    return Deployment(**data)


def test_preview_uses_pinned_sdk_volumes_and_complete_locked_command():
    preview = deployment_preview(spec(), config())
    request = preview["sdk_arguments"]
    serialized = [Volume(**x).to_dict() for x in request["volumes"]]
    assert serialized[0]["revision"] == config().model_revision
    assert serialized[0]["readOnly"] and serialized[1]["readOnly"]
    assert serialized[2]["readOnly"] is False
    assert request["namespace"] == "fixture" and request["attempts"] == 1
    assert request["timeout"] == 3480 and request["ssh"] is False
    assert request["command"][-2:] == ["--phase", "hardware_preflight"]
    assert preview["compute_allowance_usd"] == 5
    assert not preview["compute_allowance_is_account_cap"]
    assert not preview["execution_enabled"] and "secrets" not in request
    assert "paid_cli_locked" in preview["blockers"]
    # Even a fully attested fixture cannot authorize paid execution.
    full = spec(image_published=True, input_snapshot_attested=True,
                output_bucket_attested=True, gpu_budget_approved=True)
    assert "paid_cli_locked" in deployment_preview(full, config())["blockers"]


@pytest.mark.parametrize("updates", [
    {"image": "worker:latest"}, {"model_revision": "main"},
    {"output_bucket": "someone-else/output"}, {"run_id": "../escape"},
    {"input_path": "/inputs"}, {"session_seconds": 3400},
    {"phase_cap_usd": 4.0}, {"namespace": ""},
])
def test_invalid_provider_binding_fails_before_any_operation(updates):
    with pytest.raises(ValueError):
        spec(**updates)


def test_model_and_deadline_mismatch_rejected():
    with pytest.raises(ValueError, match="revision"):
        deployment_preview(spec(model_revision="b" * 40), config())
    with pytest.raises(ValueError, match="deadlines"):
        deployment_preview(spec(), config().model_copy(update={"max_wall_seconds": 3600}))


def test_mounted_input_validation_and_cli_lock(tmp_path, monkeypatch, capsys):
    model, artifacts = tmp_path / "model", tmp_path / "output"
    model.mkdir()
    artifacts.mkdir()
    (model / "tokenizer.json").write_text("{\"fixture\":true}")
    (model / "config.json").write_text("{\"model_type\":\"qwen3_5\"}")
    cfg = config().model_copy(update={"model_path": str(model),
        "model_tree_sha256": checkpoint_tree_sha256(model),
        "tokenizer_sha256": hashlib.sha256((model / "tokenizer.json").read_bytes()).hexdigest()})
    frozen = tmp_path / "config.json"
    frozen.write_text(cfg.model_dump_json())
    argv = ["--config", str(frozen), "--runtime-root", "integrations/openenv-arena",
            "--model-root", str(model), "--artifact-root", str(artifacts)]
    assert main(["--validate-inputs", *argv]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["checkpoint_tree_verified"] and not report["model_loaded"]
    assert not report["remote_durability_verified"]
    monkeypatch.setattr(Path, "read_text", lambda *a, **k: pytest.fail("Paid CLI read a file"))
    with pytest.raises(SystemExit, match="locked"):
        main(["--execute", *argv, "--output", str(tmp_path / "job")])


def test_mount_hash_drift_rejected(tmp_path):
    model, artifacts = tmp_path / "model", tmp_path / "output"
    model.mkdir()
    artifacts.mkdir()
    (model / "tokenizer.json").write_text("{}")
    cfg = config().model_copy(update={"model_path": str(model),
        "model_tree_sha256": checkpoint_tree_sha256(model),
        "tokenizer_sha256": hashlib.sha256(b"{}").hexdigest()})
    (model / "config.json").write_text("changed")
    with pytest.raises(ValueError, match="hash differs"):
        validate_session_inputs(cfg, Path("integrations/openenv-arena"), model, artifacts)
