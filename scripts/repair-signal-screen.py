"""Bounded, no-retry same-prompt proxy screen. Default is an offline plan.

No GPU training, purchase or Arena submission operation exists here. Existing
inference authorization and a privately reconciled billing receipt are required.
Provider checkpoint/thinking and the Arena chat wrapper remain unattested.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
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
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "integrations/software-repair"))
from repair_env.environment import RepairAction, RepairEnvironment, check  # noqa: E402
from repair_env.tasks import visible_files, SOURCE_PATH
from repair_env.runner import Program, Rejected  # noqa: E402

HELPER = ROOT / "integrations/openenv-arena/scripts/calibrate.py"
sys.path.insert(0, str(HELPER.parent.parent))
SPEC = importlib.util.spec_from_file_location("baseline_calibration_utilities", HELPER)
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)

TOKENIZER_SHA = "0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3"
MODEL = "Qwen/Qwen3.8-27B"
GROUPS = [("software_repair-plan-d3", 988000), ("software_repair-plan-d3", 988100)]
SAMPLES = 4
MAX_TURNS = 12
BASE = "https://router.huggingface.co/v1"


def fingerprint(value):
    return hashlib.sha256(helper.canonical(value).encode()).hexdigest()


def quote(opener, token):
    request = urllib.request.Request(BASE + "/models", headers={"Authorization": "Bearer " + token})
    with opener.open(request, timeout=15) as response:
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
        checked = datetime.fromisoformat(value["checked_at"])
        age = (datetime.now(timezone.utc) - checked).total_seconds()
        cap = Decimal(str(value["screen_cap_usd"]))
        prior = Decimal(str(value["prior_spend_usd"]))
        balance = Decimal(str(value["prepaid_balance_usd"]))
        total = Decimal(str(value["total_authorized_usd"]))
        if not 0 <= age <= 7200 or not 0 < cap <= 2 or prior + cap > total or cap > balance:
            raise ValueError("fresh reconciled existing inference allocation required")
        self.cap, self.local_lock = cap, threading.Lock()
        self.ledger = self.path.with_suffix(".reservations.jsonl")

    def reserve(self, label, prompt_bound, generated_bound, prices):
        amount = (Decimal(prompt_bound) * Decimal(str(prices["input"])) +
                  Decimal(generated_bound) * Decimal(str(prices["output"]))) / Decimal(1_000_000)
        amount *= Decimal("1.10")  # Extra margin; still a quote reservation, not invoice proof.
        with self.local_lock, self.ledger.open("a+") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
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


def episode(task_id, seed, sample, token, counter, budget, frozen, stop, deadline, prefix):
    env = RepairEnvironment()
    reset = env.reset(task_id=task_id, seed=seed)
    identity = fingerprint({"reset": reset.model_dump(), "files": visible_files(env._task)})
    messages = [{"role": "system", "content": "Operate the Python repair workspace. Inspect files, edit src/solution.py, test, then submit the repaired workspace. Emit exactly one JSON action instance, no markdown. Follow the README Python subset. Action schema: " + json.dumps(RepairAction.model_json_schema())},
                {"role": "user", "content": reset.model_dump_json()}]
    row = {"task_id": task_id, "seed": seed, "sample": sample, "prompt_sha256": identity,
           "reward": 0.0, "solved": False, "failure": None, "calls": [], "messages": messages}
    opener = urllib.request.build_opener(helper.NoRedirect(), urllib.request.ProxyHandler({}))
    generated, observed = 0, 0
    for turn in range(MAX_TURNS):
        if stop.is_set() or time.monotonic() >= deadline:
            row["failure"] = "screen_stopped"
            break
        remaining = 8192 - generated - observed
        allowance = min(4096, remaining, 16384 - counter.context(messages))
        if allowance < 1:
            row["failure"] = "episode_budget_exhausted"
            break
        try:
            if quote(opener, token) != frozen:
                stop.set()
                raise ValueError("selected metadata or quote changed")
            # UTF8 bytes plus overhead is a deliberately conservative billing reservation.
            prompt_bound = len(helper.canonical(messages).encode()) + 4096
            reserved = budget.reserve(f"{prefix}:{task_id}:{seed}:{sample}:{turn}", prompt_bound,
                                     allowance, frozen["provider"]["pricing"])
            reply = helper.provider_call(opener, BASE, token, {"model": MODEL + ":deepinfra",
                "messages": messages, "temperature": 0.7, "max_tokens": allowance,
                "response_format": {"type": "json_object"},
                "chat_template_kwargs": {"enable_thinking": True}}, 90)
        except Exception as exc:
            if isinstance(exc, ValueError) and str(exc) == "screen reservation cap exhausted":
                row["failure"] = "screen_reservation_cap_exhausted"
                stop.set()
            elif isinstance(exc, ValueError) and str(exc) == "selected metadata or quote changed":
                row["failure"] = "selected_provenance_changed"
                stop.set()
            else:
                row["failure"] = "provider_or_reservation_failure"
            row["failure_type"] = type(exc).__name__
            break
        metric = helper.metric_for(reply)
        metric.update(reserved_usd=reserved, max_tokens=allowance)
        row["calls"].append(metric)
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
            if value == {"finish": True}:
                value = {"op": "submit"}
            elif type(value) is dict and set(value) == {"action"}:
                value = value["action"]
            action = RepairAction.model_validate(value)
        except Exception:
            row["failure"] = "invalid_json_action"
            break
        observation = env.step(action)
        text = observation.model_dump_json()
        observed += counter.count(text)
        messages.append({"role": "user", "content": text})
        if generated + observed > 8192 or counter.context(messages) > 16384:
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
    row.update(generation_tokens=generated, observation_tokens=observed,
               arena_budget_matched=False, thinking_verified=False)
    return row


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--budget-receipt", type=Path)
    parser.add_argument("--tokenizer", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({"executed": False, "groups": GROUPS, "samples_per_group": SAMPLES,
                          "max_calls": len(GROUPS) * SAMPLES * MAX_TURNS, "max_quoted_reservations_usd": 2}))
        return 0
    budget = DollarReservations(args.budget_receipt)
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        raise ValueError("existing private environment authentication required")
    counter = helper.load_counter(argparse.Namespace(accounting="arena", tokenizer_json=args.tokenizer,
                                                   tokenizer_sha256=TOKENIZER_SHA))
    opener = urllib.request.build_opener(helper.NoRedirect(), urllib.request.ProxyHandler({}))
    frozen = quote(opener, token)
    args.output.mkdir(exist_ok=False)
    protocol = {"groups": GROUPS, "samples_per_group": SAMPLES, "provider": frozen,
        "source_files_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__), HELPER, *sorted((ROOT / "integrations/software-repair/repair_env").glob("*.py"))]},
        "tokenizer_sha256": TOKENIZER_SHA, "thinking_requested": True, "thinking_verified": False,
        "max_calls": len(GROUPS) * SAMPLES * MAX_TURNS, "max_turns_per_rollout": MAX_TURNS, "no_retry": True,
        "arena_budget_matched": False, "checkpoint_attested": False,
        "is_training": False, "private_arena_score": None}
    (args.output / "protocol.json").write_text(json.dumps(protocol, indent=2))
    stop, deadline, records = threading.Event(), time.monotonic() + 1200, []
    with (args.output / "episodes.jsonl").open("x") as stream:
        for task_id, seed in GROUPS:
            if stop.is_set():
                break
            with ThreadPoolExecutor(max_workers=SAMPLES) as pool:
                futures = [pool.submit(episode, task_id, seed, i, token, counter, budget,
                    frozen, stop, deadline, args.output.name) for i in range(SAMPLES)]
                for future in futures:
                    try:
                        record = future.result()
                    except Exception as exc:
                        stop.set()
                        record = {"task_id": task_id, "seed": seed, "failure": "screen_internal_failure",
                                  "failure_type": type(exc).__name__, "reward": 0, "solved": False}
                    raw = json.dumps(record).replace(token, "[REDACTED]")
                    stream.write(raw + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                    records.append(record)
    summary = {"rollouts": len(records), "unique_prompt_groups": len(GROUPS),
        "full_solves": sum(row["solved"] for row in records),
        "groups": [{"task_id": task, "seed": seed,
            "rewards": [r["reward"] for r in records if r["task_id"] == task and r["seed"] == seed],
            "failures": [r["failure"] for r in records if r["task_id"] == task and r["seed"] == seed],
            "prompt_hashes": sorted({r.get("prompt_sha256", "missing") for r in records if r["task_id"] == task and r["seed"] == seed})}
            for task, seed in GROUPS], "is_training": False, "arena_budget_matched": False}
    (args.output / "complete.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
