"""Bounded, no-retry same-prompt proxy screen. Default is an offline plan.

No GPU training, purchase or Arena submission operation exists here. Existing
inference authorization and a privately reconciled billing receipt are required.
Provider checkpoint/thinking and the Arena chat wrapper remain unattested.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from decimal import Decimal
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from provider_stream import provider_call as stream_provider_call
sys.path.insert(0, str(ROOT / "integrations/software-repair"))
from repair_env.environment import RepairAction, RepairEnvironment, check  # noqa: E402
from repair_env.direct_environment import DirectRepairAction, DirectRepairEnvironment
from repair_env.tasks import visible_files, SOURCE_PATH
from repair_env.runner import Program, Rejected  # noqa: E402
sys.path.insert(0, str(ROOT / "integrations/software-repair/scripts"))
from screen_profiles import get_profile, MODEL, TOKENIZER_SHA, SAMPLES, MAX_TURNS, REQUEST_TIMEOUT_S
from screen_deadline import DeadlineExceeded, request_timeout, run_bounded

_now = time.monotonic

HELPER = ROOT / "integrations/openenv-arena/scripts/calibrate.py"
sys.path.insert(0, str(HELPER.parent.parent))
SPEC = importlib.util.spec_from_file_location("baseline_calibration_utilities", HELPER)
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)

GROUPS = get_profile("release", "screen")["groups"]
CONFIRM_GROUPS = get_profile("release", "confirm")["groups"]
BASE = "https://router.huggingface.co/v1"


def fingerprint(value):
    return hashlib.sha256(helper.canonical(value).encode()).hexdigest()


def quote(opener, token, timeout=15):
    request = urllib.request.Request(BASE + "/models", headers={"Authorization": "Bearer " + token})
    with opener.open(request, timeout=timeout) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("model catalog exceeds bound")
    rows = [row for row in json.loads(raw)["data"] if row.get("id") == MODEL]
    if len(rows) != 1:
        raise ValueError("selected model disappeared or ambiguous")
    row = rows[0]
    routes = [p for p in row["providers"] if p.get("provider") == "deepinfra"]
    if len(routes) != 1 or routes[0].get("status") != "live":
        raise ValueError("bound route unavailable")
    route = {k: v for k, v in routes[0].items() if k not in ("first_token_latency_ms", "throughput")}
    prices = route["pricing"]
    if (type(prices.get("input")) not in (int, float) or
            type(prices.get("output")) not in (int, float) or
            not 0 <= prices["input"] <= 1 or not 0 < prices["output"] <= 3):
        raise ValueError("selected provider price outside frozen screen bounds")
    return {"id": row["id"], "created": row.get("created"), "owned_by": row.get("owned_by"),
            "architecture": row.get("architecture"), "provider": route}


class DollarReservations:
    """Append-before-call reservations never refunded, even for provider failures."""
    def __init__(self, receipt):
        self.path = Path(receipt)
        value = json.loads(self.path.read_text())
        if value.get("closed_for_new_calls") is True:
            raise ValueError("inference allocation is closed for new calls")
        checked = datetime.fromisoformat(value["checked_at"])
        age = (datetime.now(timezone.utc) - checked).total_seconds()
        cap = Decimal(str(value["screen_cap_usd"]))
        prior = Decimal(str(value["prior_spend_usd"]))
        balance = Decimal(str(value["prepaid_balance_usd"]))
        total = Decimal(str(value["total_authorized_usd"]))
        if not 0 <= age <= 7200 or not 0 < cap <= 2 or prior + cap > total or cap > balance:
            raise ValueError("fresh reconciled existing inference allocation required")
        self.cap, self.local_lock = cap, threading.Lock()
        self.checked_at = checked
        self.ledger = self.path.with_suffix(".reservations.jsonl")

    def reserve(self, label, prompt_bound, generated_bound, prices):
        amount = (Decimal(prompt_bound) * Decimal(str(prices["input"])) +
                  Decimal(generated_bound) * Decimal(str(prices["output"]))) / Decimal(1_000_000)
        amount *= Decimal("1.10")  # Extra margin; still a quote reservation, not invoice proof.
        with self.local_lock, self.ledger.open("a+") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            age = (datetime.now(timezone.utc) - self.checked_at).total_seconds()
            if not 0 <= age <= 7200:
                raise ValueError("billing observation expired")
            stream.seek(0)
            rows = [json.loads(line) for line in stream if line.strip()]
            if any(row["label"] == label for row in rows):
                raise ValueError("duplicate call reservation")
            used = sum((Decimal(row["usd"]) for row in rows), Decimal(0))
            if used + amount > self.cap:
                raise ValueError("screen reservation cap exhausted")
            record = {"label": label, "usd": str(amount), "prompt_bound": prompt_bound,
                      "generation_bound": generated_bound}
            stream.write(json.dumps(record) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        return float(amount)


def failed_finish_diagnostic(env, last_observation):
    """Score locally after failure without changing its label or valid reward."""
    try:
        terminal = last_observation if last_observation.done else env.step(
            getattr(env, "_finish_action", RepairAction(op="submit")))
        diagnostic = {"available": True, "origin": "local_terminal_diagnostic",
            "finish_action_sent": not last_observation.done, "observed_done": terminal.done,
            "terminal_reward": float(terminal.reward), "environment_error": bool(terminal.error),
            "counts_as_valid_completion": False}
        try:
            _, outcomes = check(Program(env._files[SOURCE_PATH]), env._task, env._task.hidden, details=True)
            diagnostic["hidden_execution_rejections"] = sum(item["error"] is not None for item in outcomes)
            diagnostic["hidden_wrong_answers"] = sum(not item["passed"] and item["error"] is None for item in outcomes)
        except Exception as exc:
            diagnostic["grader_error_type"] = type(exc).__name__
        return diagnostic
    except Exception as exc:
        return {"available": False, "error_type": type(exc).__name__, "counts_as_valid_completion": False}


def episode(task_id, seed, sample, token, counter, budget, frozen, stop, deadline, prefix, settings=None):
    progress = {}
    try:
        return _episode(task_id, seed, sample, token, counter, budget, frozen, stop, deadline, prefix, progress, settings)
    except Exception as exc:
        stop.set()
        # Preserve only actually observed state; never synthesize reset/call
        # identities for an episode which failed before capturing them.
        row = progress.get("row", {"task_id": task_id, "seed": seed, "sample": sample,
                                   "calls": [], "prompt_identity_unavailable": True})
        row.update(failure="screen_internal_failure", failure_type=type(exc).__name__,
                   reward=0, solved=False, arena_budget_matched=False, thinking_verified=False)
        if "last_observation" in progress:
            row["termination_grading"] = failed_finish_diagnostic(progress["env"], progress["last_observation"])
        return row


def _episode(task_id, seed, sample, token, counter, budget, frozen, stop, deadline, prefix, progress, settings=None):
    settings = settings or get_profile("release", "screen")["sampling_settings"]
    episode_units = settings["episode_generation_observation_units"]
    context_units = settings["context_units"]
    if (type(episode_units) is not int or type(context_units) is not int or
            not 1 <= episode_units <= context_units <= 32768):
        raise ValueError("invalid frozen episode capacity")
    direct = settings.get("interface") == "direct_code"
    env = DirectRepairEnvironment() if direct else RepairEnvironment()
    action_type = DirectRepairAction if direct else RepairAction
    reset = env.reset(task_id=task_id, seed=seed)
    last_observation = reset
    progress.update(env=env, last_observation=reset)
    identity = fingerprint({"reset": reset.model_dump(), "files": visible_files(env._task)})
    instruction = ("Repair the supplied Python module. Return one JSON object whose content field is the complete repaired code. No markdown, schema copying, diff or tool command. " if direct else
                   "Operate the Python repair workspace. Inspect files, edit src/solution.py, test, then submit the repaired workspace. ")
    messages = [{"role": "system", "content": instruction + "Emit exactly one JSON action instance, no markdown. Follow the documented Python subset. Action schema: " + json.dumps(action_type.model_json_schema())},
                {"role": "user", "content": reset.model_dump_json()}]
    row = {"task_id": task_id, "seed": seed, "sample": sample, "prompt_sha256": identity,
           "reward": 0.0, "solved": False, "failure": None, "calls": [], "messages": messages}
    progress["row"] = row
    opener = urllib.request.build_opener(helper.NoRedirect(), urllib.request.ProxyHandler({}))
    generated, observed = 0, 0
    for turn in range(settings.get("max_actions", MAX_TURNS)):
        if stop.is_set() or _now() >= deadline:
            row["failure"] = "screen_stopped"
            break
        remaining = episode_units - generated - observed
        allowance = min(settings.get("max_generation_per_call", 4096), remaining, context_units - counter.context(messages))
        if allowance < 1:
            row["failure"] = "episode_budget_exhausted"
            break
        operation = "selected_model_quote"
        try:
            if quote(opener, token, request_timeout(deadline, 15, now=_now())) != frozen:
                stop.set()
                raise ValueError("selected metadata or quote changed")
            call_timeout = settings.get("request_timeout_seconds", REQUEST_TIMEOUT_S)
            if type(call_timeout) not in (int, float) or not 0 < call_timeout <= 360:
                raise ValueError("bounded provider wait required")
            request_timeout(deadline, call_timeout, now=_now())  # No reservation after deadline.
            if stop.is_set():
                raise DeadlineExceeded("screen stopped before reservation")
            # UTF8 bytes plus overhead is a deliberately conservative billing reservation.
            prompt_bound = len(helper.canonical(messages).encode()) + 4096
            call_label = f"{prefix}:{task_id}:{seed}:{sample}:{turn}"
            operation = "dollar_reservation"
            reserved = budget.reserve(call_label, prompt_bound,
                                     allowance, frozen["provider"]["pricing"])
            if stop.is_set():
                raise DeadlineExceeded("screen stopped before provider call")
            operation = "model_provider"
            call = stream_provider_call if settings.get("provider_streaming") else helper.provider_call
            reply = call(opener, BASE, token, {"model": MODEL + ":deepinfra",
                "messages": messages, "temperature": 0.7, "max_tokens": allowance,
                "response_format": {"type": "json_object"},
                "chat_template_kwargs": {"enable_thinking": True}},
                request_timeout(deadline, call_timeout, now=_now()))
        except Exception as exc:
            if isinstance(exc, DeadlineExceeded):
                row["failure"] = "screen_stopped"
                stop.set()
            elif isinstance(exc, ValueError) and str(exc) == "screen reservation cap exhausted":
                row["failure"] = "screen_reservation_cap_exhausted"
                stop.set()
            elif isinstance(exc, ValueError) and str(exc) == "billing observation expired":
                row["failure"] = "billing_observation_expired"
                stop.set()
            elif isinstance(exc, ValueError) and str(exc) == "selected metadata or quote changed":
                row["failure"] = "selected_provenance_changed"
                stop.set()
            else:
                row["failure"] = "provider_or_reservation_failure"
            if operation == "selected_model_quote" and isinstance(exc, ValueError):
                stop.set()  # Removal/malformed metadata cannot admit any further calls.
            row["failure_type"] = type(exc).__name__
            row["failure_operation"] = operation
            safe_codes = {"model catalog exceeds bound": "catalog_size_limit",
                "selected model disappeared or ambiguous": "selected_model_missing_or_ambiguous",
                "bound route unavailable": "bound_provider_unavailable",
                "selected provider price outside frozen screen bounds": "quote_outside_bounds",
                "selected metadata or quote changed": "selected_provenance_changed"}
            row["failure_code"] = safe_codes.get(str(exc), type(exc).__name__)
            if isinstance(exc, urllib.error.HTTPError):
                row["provider_http_status"] = exc.code
            break
        identifier = reply.get("id")
        # Save actual response identity before parsing usage/choices; a parser
        # failure must not erase an already observed provider call.
        metric = {"client_call_label": call_label, "reserved_usd": reserved, "max_tokens": allowance,
            "provider_response_id_sha256": hashlib.sha256(identifier.encode()).hexdigest()
                if isinstance(identifier, str) and identifier else None}
        row["calls"].append(metric)
        metric.update(helper.metric_for(reply))
        message = reply["choices"][0]["message"]
        content = message.get("content") or ""
        fields, reasoning, _, _, error, leaked = helper.reasoning_payload(message, token)
        if leaked or token in content:
            stop.set()
            row["failure"] = "credential_redaction_guard"
            break
        if (metric["prompt_tokens"] is None or metric["completion_tokens"] is None or
                metric["prompt_tokens"] > prompt_bound or metric["completion_tokens"] > allowance):
            stop.set()
            row["failure"] = "provider_usage_unverified_or_exceeded_reservation"
            break
        generated += metric["completion_tokens"]
        messages.append({"role": "assistant", "content": content, **fields})
        if error or metric["finish_reason"] in ("length", "content_filter"):
            row["failure"] = "completion_truncated" if metric["finish_reason"] == "length" else "provider_response_failure"
            break
        try:
            value = json.loads(content)
            if type(value) is dict and set(value) == {"finish"} and value["finish"] is True:
                value = {"content": ""} if direct else {"op": "submit"}
            elif type(value) is dict and set(value) == {"action"}:
                value = value["action"]
            action = action_type.model_validate(value)
        except Exception:
            row["failure"] = "invalid_json_action"
            break
        observation = env.step(action)
        last_observation = observation
        progress["last_observation"] = observation
        text = observation.model_dump_json()
        observed += counter.count(text)
        messages.append({"role": "user", "content": text})
        if generated + observed > episode_units or counter.context(messages) > context_units:
            row["failure"] = "episode_budget_exceeded"
            break
        if observation.done:
            row.update(reward=float(observation.reward), solved=observation.reward == 1.0)
            if observation.error:
                row["failure"] = "environment_tool_budget_exhausted" if observation.error.startswith("step budget exhausted") else "environment_failure"
            try:
                _, outcomes = check(Program(env._files[SOURCE_PATH]), env._task, env._task.hidden, details=True)
                row["hidden_execution_rejections"] = sum(item["error"] is not None for item in outcomes)
                row["hidden_wrong_answers"] = sum(not item["passed"] and item["error"] is None for item in outcomes)
                if row["hidden_execution_rejections"]:
                    row["failure"] = "candidate_execution_failure"
            except Rejected:
                row["failure"] = "invalid_candidate_code"
            break
    else:
        row["failure"] = "screen_tool_budget_exhausted"
    if row["failure"]:
        row["termination_grading"] = failed_finish_diagnostic(env, last_observation)
    row.update(generation_tokens=generated, observation_tokens=observed,
               arena_budget_matched=False, thinking_verified=False)
    return row


def _execute(deadline, args, profile):
    groups = profile["groups"]
    samples = profile["samples_per_group"]
    args.output.mkdir(exist_ok=False)  # Claim a fresh root before auth or HTTP.
    request_timeout(deadline, 15, now=_now())
    budget = DollarReservations(args.budget_receipt)
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        raise ValueError("existing private environment authentication required")
    counter = helper.load_counter(argparse.Namespace(accounting="arena", tokenizer_json=args.tokenizer,
                                                   tokenizer_sha256=TOKENIZER_SHA))
    opener = urllib.request.build_opener(helper.NoRedirect(), urllib.request.ProxyHandler({}))
    frozen = quote(opener, token, request_timeout(deadline, 15, now=_now()))
    request_timeout(deadline, 90, now=_now())
    protocol = {"stage": args.stage, "profile": args.profile, "groups": groups,
        "signal_task_ids": profile["signal_task_ids"], "sampling_settings": profile["sampling_settings"],
        "required_productive_groups": profile.get("required_productive_groups", 1),
        "samples_per_group": samples, "purpose": profile.get("purpose", "signal_screen"),
        "provider": frozen,
        "source_files_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__), HELPER, ROOT / "scripts/provider_stream.py",
                      ROOT / "integrations/software-repair/scripts/screen_profiles.py",
                      ROOT / "integrations/software-repair/scripts/analyze_screen.py",
                      ROOT / "integrations/software-repair/scripts/screen_deadline.py",
                      *sorted((ROOT / "integrations/software-repair/repair_env").glob("*.py"))]},
        "tokenizer_sha256": TOKENIZER_SHA, "thinking_requested": True, "thinking_verified": False,
        "max_calls": profile["max_calls"], "max_turns_per_rollout": profile["sampling_settings"].get("max_actions", MAX_TURNS), "no_retry": True,
        "arena_budget_matched": False, "checkpoint_attested": False,
        "is_training": False, "private_arena_score": None,
        "worker_supervision": {"required": True, "wall_seconds": profile["sampling_settings"]["stage_wall_seconds"]},
        "planned_confirmation_groups": profile["planned_confirmation_groups"],
        "confirmation_requires_genuine_signal": True}
    (args.output / "protocol.json").write_text(json.dumps(protocol, indent=2))
    stop, records = threading.Event(), []
    with (args.output / "episodes.jsonl").open("x") as stream:
        for task_id, seed in groups:
            if stop.is_set():
                break
            with ThreadPoolExecutor(max_workers=samples) as pool:
                futures = {pool.submit(episode, task_id, seed, i, token, counter, budget,
                    frozen, stop, deadline, args.output.name, profile["sampling_settings"]): i for i in range(samples)}
                for future in as_completed(futures):
                    sample = futures[future]
                    try:
                        record = future.result()
                    except Exception as exc:
                        stop.set()
                        record = {"task_id": task_id, "seed": seed, "sample": sample,
                                  "failure": "screen_internal_failure",
                                  "failure_type": type(exc).__name__, "reward": 0, "solved": False,
                                  "calls": [], "prompt_identity_unavailable": True}
                    raw = json.dumps(record).replace(token, "[REDACTED]")
                    stream.write(raw + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                    records.append(record)
    records.sort(key=lambda row: (row["task_id"], row["seed"], row["sample"]))
    summary = {"rollouts": len(records), "unique_prompt_groups": len(groups),
        "full_solves": sum(row["solved"] and not row["failure"] for row in records),
        "failed_episode_terminal_diagnostics": sum("termination_grading" in row for row in records),
        "groups": [{"task_id": task, "seed": seed,
            "rewards": [r["reward"] for r in records if r["task_id"] == task and r["seed"] == seed],
            "failures": [r["failure"] for r in records if r["task_id"] == task and r["seed"] == seed],
            "prompt_hashes": sorted({r.get("prompt_sha256", "missing") for r in records if r["task_id"] == task and r["seed"] == seed})}
            for task, seed in groups], "is_training": False, "arena_budget_matched": False}
    (args.output / "complete.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--profile",
        choices=("release", "replay_compare", "merge_compare", "merge_probe",
                 "repair_reliability", "release_witness", "release_witness_capacity",
                 "release_generalization", "release_stream_probe", "release_generalization_stream",
                 "direct_release", "direct_release_control", "direct_synthesis", "direct_capacity_control"),
        default="release",
    )
    parser.add_argument("--stage", choices=("screen", "confirm"), default="screen")
    parser.add_argument("--budget-receipt", type=Path)
    parser.add_argument("--tokenizer", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    profile = get_profile(args.profile, args.stage)
    if not args.execute:
        print(json.dumps({**profile, "executed": False, "max_quoted_reservations_usd": 2}))
        return 0
    if not profile["execution_enabled"]:
        raise ValueError("comparison is plan-only; paid execution is disabled")
    if args.output is None or args.budget_receipt is None or args.tokenizer is None:
        raise ValueError("fresh output, existing budget receipt and pinned tokenizer paths required")
    if args.output.exists():
        raise ValueError("screen output already exists")
    receipt = args.output.with_name(args.output.name + ".worker.jsonl")
    result = run_bounded(_execute, (args, profile), profile["sampling_settings"]["stage_wall_seconds"], receipt)
    print(json.dumps({"worker": result, "is_training": False}))
    return 0 if result["status"] == "completed" and result["shutdown_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
