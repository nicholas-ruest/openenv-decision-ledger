"""All approvals, credentials and HTTP responses here are synthetic fixtures."""
import copy
import hashlib
import hmac
import json
import time
from pathlib import Path

import httpx
import pytest
from huggingface_hub import Volume
from huggingface_hub.hf_api import _create_job_spec

from training.approval import KEY_ENV, canonical, digest, verify_approval
from training.config import TrainingConfig
from training.deployment import Deployment, deployment_preview
from training.hardware_preflight import main as worker_main, run_bound_worker
from training.launch_preflight import approved_payload, launch_once, main as launch_main
from training.provider_http import BoundedJobsApi

JOB = "a" * 24


@pytest.fixture
def approved(monkeypatch):
    monkeypatch.setenv(KEY_ENV, "f" * 64)
    monkeypatch.setenv("HF_TOKEN", "synthetic-test-credential")
    config = TrainingConfig.model_validate_json(Path("config/private-training-preparation.json").read_text())
    spec = Deployment(namespace="fixture", image="ghcr.io/fixture/worker@sha256:" + "a" * 64,
        model_revision=config.model_revision, input_bucket="fixture/input", output_bucket="fixture/output",
        input_path="snapshot", run_id="hardware-1", image_published=True,
        input_snapshot_attested=True, output_bucket_attested=True, gpu_budget_approved=True)
    def sign(cfg=config, request=spec, **updates):
        claims = dict(request_sha256=digest(request.model_dump()), config_sha256=digest(cfg.model_dump()),
            run_id=request.run_id, phase=request.phase, expires_at=time.time() + 3600, max_compute_usd=5.0)
        claims.update(updates)
        return dict(claims=claims, signature=hmac.new(bytes.fromhex("f" * 64), canonical(claims), hashlib.sha256).hexdigest())
    return spec, config, sign


@pytest.mark.parametrize("entry", [worker_main, launch_main])
def test_default_lock_before_file_or_network(monkeypatch, entry):
    monkeypatch.delenv(KEY_ENV, raising=False)
    monkeypatch.setattr(Path, "read_text", lambda *a, **k: pytest.fail("read before approval"))
    args = ["--execute", "--deployment", "missing", "--config", "missing", "--approval", "missing"]
    if entry is launch_main:
        args += ["--journal-root", "missing"]
    with pytest.raises(PermissionError, match="locked"):
        entry(args)


@pytest.mark.parametrize("change", ["signature", "expired", "cap", "config", "image", "pilot", "hfkey"])
def test_request_binding_rejects_drift(approved, monkeypatch, change):
    spec, config, sign = approved
    receipt = sign()
    if change == "signature":
        receipt["signature"] = "0" * 64
    elif change == "expired":
        receipt = sign(expires_at=time.time() - 1)
    elif change == "cap":
        receipt = sign(max_compute_usd=4.0)
    elif change == "config":
        config = config.model_copy(update={"max_optimizer_steps": 200})
    elif change == "image":
        spec = spec.model_copy(update={"image": "ghcr.io/fixture/worker@sha256:" + "b" * 64})
    elif change == "pilot":
        spec = spec.model_copy(update={"phase": "pilot"})
        receipt = sign(request=spec)
    else:
        monkeypatch.setenv("HF_TOKEN", "f" * 64)
    with pytest.raises(PermissionError):
        verify_approval(receipt, spec, config)


def test_payload_matches_pinned_sdk_and_never_contains_hf_token(approved):
    spec, config, sign = approved
    payload = approved_payload(spec, config, sign())
    preview = deployment_preview(spec, config)["sdk_arguments"]
    expected = _create_job_spec(image=spec.image, command=payload["command"],
        env=preview["env"], secrets={KEY_ENV: "f" * 64}, flavor="h200", timeout=3480,
        attempts=1, labels={"openenv_run_id": spec.run_id}, volumes=[Volume(**x) for x in preview["volumes"]])
    assert payload == expected
    assert "synthetic-test-credential" not in json.dumps(payload)
    assert payload["command"][2] == "training.hardware_preflight"


@pytest.mark.parametrize("mode", ["success", "lost_response", "invalid_id", "cancel"])
def test_once_only_creation_and_terminal_observation(approved, tmp_path, mode):
    spec, config, sign = approved
    seen = []
    def handler(request):
        seen.append((request.method, request.url.path))
        if request.url.path == "/api/jobs/fixture":
            body = json.loads(request.content)
            assert "synthetic-test-credential" not in json.dumps(body)
            assert request.headers["authorization"] == "Bearer synthetic-test-credential"
            if mode == "lost_response":
                raise httpx.ReadTimeout("synthetic ambiguous response")
            return httpx.Response(200, json={"id": JOB if mode != "invalid_id" else "unknown"})
        if request.url.path.endswith("/cancel"):
            return httpx.Response(200, json={})
        return httpx.Response(200, json={"status": {"stage": "RUNNING" if mode == "cancel" and
            not any(p.endswith("/cancel") for _, p in seen) else "COMPLETED"}})
    provider = BoundedJobsApi("fixture", transport=httpx.MockTransport(handler),
                              allow_creation=True, allow_cancellation=True)
    kwargs = {}
    if mode == "cancel":
        from training.job_control import monitor_existing
        tick = [0.0]
        def pause(seconds):
            tick[0] += seconds
        kwargs["monitor"] = lambda p, job_id, **k: monitor_existing(p, job_id, seconds=1,
            clock=lambda: tick[0], pause=pause)
    result = launch_once(spec, config, sign(), tmp_path, provider=provider, **kwargs)
    if mode in {"lost_response", "invalid_id"}:
        assert result["status"] == "creation_unknown" and not result["terminal_verified"]
        assert len(seen) == 1
    else:
        assert result["terminal_verified"] and result["job_id"] == JOB
        assert result["cancel_requested"] == (mode == "cancel")
    with pytest.raises(FileExistsError):
        launch_once(spec, config, sign(), tmp_path, provider=provider)
    assert sum(m == "POST" and p == "/api/jobs/fixture" for m, p in seen) == 1
    assert "synthetic-test-credential" not in (tmp_path / "hardware-1.json").read_text()
    assert "f" * 64 not in (tmp_path / "hardware-1.json").read_text()


def test_provider_mutation_capability_defaults_off():
    with pytest.raises(PermissionError):
        BoundedJobsApi("fixture").create_job({})


def test_loading_failure_gets_durable_report_and_replay_guard(approved, tmp_path):
    spec, config, sign = approved
    mount = tmp_path / "mount"
    mount.mkdir()
    def fail(*a, **k):
        raise RuntimeError("synthetic loading error; do not export this text")
    kwargs = dict(runtime_root=Path("integrations/openenv-arena"), model_root=tmp_path / "model",
        artifact_root=mount, output=tmp_path / spec.run_id,
        input_validator=lambda *a: None, session_runner=fail)
    result = run_bound_worker(spec, config, sign(), **kwargs)
    assert result["status"] == "failed" and result["error_type"] == "RuntimeError"
    assert result["provider_billing_stopped"] is None
    assert "synthetic loading error" not in json.dumps(result)
    assert json.loads((mount / "preflight-reports/hardware-1.json").read_text()) == result
    with pytest.raises(FileExistsError):
        run_bound_worker(spec, config, sign(), **kwargs)


def test_approved_dispatch_real_tiny_optimizer_save_reload(approved, tmp_path):
    from arena_env.environment import ArenaAction, ArenaEnvironment
    from arena_env.tasks import make_task, oracle_answer
    from training.adapter import encode
    from training.cpu_smoke import tiny_components
    from training.session import run_session
    import torch
    torch.set_num_threads(2)
    spec, config, sign = approved
    config = config.model_copy(update={"max_steps": 2, "max_completion_tokens": 512,
        "max_context_tokens": 4096, "max_optimizer_steps": 1, "thinking": False})
    expected = oracle_answer(make_task("software_change", 970000, 2))
    partial = copy.deepcopy(expected)
    partial.pop("build_order")
    actions = [json.dumps({"op": "submit", "answer": x}) for x in [expected, partial, {}, expected]]
    env = ArenaEnvironment()
    reset = env.reset(task_id="software_change-d2", seed=970000).model_dump_json()
    read = env.step(ArenaAction(op="read", path="*")).model_dump_json()
    bundle = tiny_components([reset, read, *actions], "qwen3_5")
    def sample(ids, occurrence, turn, allowance):
        action = '{"op":"read","path":"*"}' if turn == 0 else actions[occurrence % 4]
        return encode(bundle[1], action + "<|im_end|>")
    def diagnostic(cfg, runtime, output, **kwargs):
        return run_session(cfg, runtime, output, bundle=bundle, sampler=sample, diagnostic=True, **kwargs)
    mount = tmp_path / "mount"
    mount.mkdir()
    result = run_bound_worker(spec, config, sign(cfg=config),
        runtime_root=Path("integrations/openenv-arena"), model_root=tmp_path / "model",
        artifact_root=mount, output=tmp_path / spec.run_id,
        input_validator=lambda *a: None, session_runner=diagnostic)
    assert result["status"] == "completed", result
    session = result["session"]
    assert session["optimizer_steps"] == 1 and session["adapter_changed"]
    assert session["reload_equal"] and session["mounted_export"]["copy_verified"]
    assert not session["target_model_training"] and not session["gpu_fit_verified"]
