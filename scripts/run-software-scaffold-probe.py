"""Bounded 16-call proxy probe; no training, publication, retry or submission."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
TASKS = ("software_repair-ignore-d3", "software_repair-ignore-d4")
SEEDS = (2180000, 2180100)
RUNTIME = "0b8ccc3ca70a67fed5fc5837b69022261cc60497"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def classify(row):
    failure = row.get("failure")
    if failure is None:
        return None
    if failure in ("invalid_json_action", "invalid_candidate_code"):
        return "format"
    if failure == "completion_truncated":
        return "truncation"
    if failure in ("environment_failure", "candidate_execution_failure"):
        return "execution"
    if any(word in failure for word in ("budget", "reservation", "billing", "stopped")):
        return "budget"
    return "provider"  # Unknown/internal failures stay excluded, never semantic wrong.


def capture(base, task, seed):
    env = base.DirectRepairEnvironment()
    reset = env.reset(task_id=task, seed=seed)
    files = base.visible_files(env._task)
    instruction = "Repair the supplied Python module. Return one JSON object whose content field is the complete repaired code. No markdown, schema copying, diff or tool command. "
    messages = [{"role": "system", "content": instruction + "Emit exactly one JSON action instance, no markdown. Follow the documented Python subset. Action schema: " + json.dumps(base.DirectRepairAction.model_json_schema())},
                {"role": "user", "content": reset.model_dump_json()}]
    cases = [[case.args, case.expected] for case in env._task.public + env._task.hidden]
    return {"task_id": task, "seed": seed, "reset": reset.model_dump(), "files": files,
            "messages": messages, "case_sha256": digest(cases),
            "reset_sha256": digest(reset.model_dump()), "workspace_sha256": digest(files),
            "base_prompt_sha256": base.fingerprint({"reset": reset.model_dump(), "files": files}),
            "prompt_sha256": digest(messages),
            "prompt_bound": len(base.helper.canonical(messages).encode()) + 4096}


def normalize(row, expected, settings_sha):
    if row.get("prompt_sha256") != expected["base_prompt_sha256"]:
        raise ValueError("actual reset differs from frozen preflight")
    if row.get("messages", [])[:2] != expected["messages"]:
        raise ValueError("actual model request differs from preflight")
    calls = row.get("calls", [])
    if len(calls) > 1:
        raise ValueError("single-call protocol exceeded")
    metric = calls[0] if calls else {}
    label = metric.get("client_call_label") or f"not-admitted:{row['task_id']}:{row['seed']}:{row['sample']}"
    return {"task_id": row["task_id"], "seed": row["seed"], "sample": row["sample"],
            "runtime_source": RUNTIME, "settings_sha256": settings_sha,
            **{key: expected[key] for key in ("case_sha256", "reset_sha256", "workspace_sha256", "prompt_sha256")},
            "client_call_label": label, "provider_response_id_sha256": metric.get("provider_response_id_sha256"),
            "failure": classify(row), "raw_failure": row.get("failure"),
            "provider_call_observed": bool(calls), "reward": row.get("reward")}


def collect(base, jobs, token, counter, budget, frozen, settings, deadline, prefix, save):
    stop = threading.Event()
    records = []
    # Only four active samples; a fatal guard stops admission of later groups.
    for expected in jobs:
        if stop.is_set() or time.monotonic() >= deadline:
            break
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(base.episode, expected["task_id"], expected["seed"], sample,
                       token, counter, budget, frozen, stop, deadline, prefix, settings) for sample in range(4)]
            group_rows = []
            for future in futures:
                row = future.result()
                save(row)
                group_rows.append(row)
            for row in group_rows:
                records.append(normalize(row, expected, digest({"settings": settings, "provider": frozen})))
    return records


def execute(args):
    if args.output.exists():
        raise ValueError("fresh output root required")
    expected_hashes = json.loads((ROOT / "config/software-probe-source-hashes-20261027.json").read_text())
    for name, sha in expected_hashes.items():
        if hashlib.sha256((args.runtime_root / name).read_bytes()).hexdigest() != sha:
            raise ValueError("frozen runtime/proxy dependency changed")
    base = load("frozen_probe_base", args.runtime_root / "scripts/repair-signal-screen.py")
    budget = base.DollarReservations(args.receipt)
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        raise ValueError("existing environment credential required")
    counter = base.helper.load_counter(argparse.Namespace(accounting="arena", tokenizer_json=args.tokenizer,
                                                         tokenizer_sha256=base.TOKENIZER_SHA))
    opener = base.urllib.request.build_opener(base.helper.NoRedirect(), base.urllib.request.ProxyHandler({}))
    frozen = base.quote(opener, token)
    settings = base.get_profile("kv_components", "screen")["sampling_settings"]
    settings["stage_wall_seconds"] = 1800
    jobs = [capture(base, task, seed) for task in TASKS for seed in SEEDS]
    for job in jobs:
        if any(capture(base, job["task_id"], job["seed"])["base_prompt_sha256"] !=
               job["base_prompt_sha256"] for _ in range(3)):
            raise ValueError("repeated native resets are not identical")
    ledger = [json.loads(x) for x in budget.ledger.read_text().splitlines() if x]
    remaining = budget.cap - sum((Decimal(x["usd"]) for x in ledger), Decimal(0))
    admission = load("probe_admission", ROOT / "scripts/stage-phase-admission.py")
    quote = admission.admit(16, [job["prompt_bound"] for job in jobs for _ in range(4)],
                            8192, frozen["provider"]["pricing"], remaining)
    if not quote["admitted"]:
        raise ValueError("entire scaffold phase cannot fit existing allocation")
    args.output.mkdir()
    (args.output / "protocol.json").write_text(json.dumps({"tasks": TASKS, "seeds": SEEDS, "calls": 16,
        "runtime_source": RUNTIME, "source_hashes": expected_hashes, "settings": settings,
        "provider": frozen, "joint_model_baseline": False, "thinking_attested": False,
        "checkpoint_attested": False, "arena_wrapper_equivalent": False}, indent=2))
    (args.output / "resets.json").write_text(json.dumps(jobs, indent=2))
    with (args.output / "raw-episodes.jsonl").open("x") as stream:
        def save(row):
            stream.write(json.dumps(row) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        records = collect(base, jobs, token, counter, budget, frozen, settings,
                          time.monotonic() + 1800, args.output.name, save)
    (args.output / "records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    assessor = load("probe_assessor", ROOT / "scripts/assess-software-stage-comparison.py")
    report = assessor.assess(records, "screen", assessor.TASKS[1:])
    report.update(is_training=False, model_improvement_claim=False, promotion=False,
                  raw_records_sha256=hashlib.sha256((args.output / "raw-episodes.jsonl").read_bytes()).hexdigest())
    (args.output / "complete.json").write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--execute", action="store_true")
    for name in ("runtime-root", "output", "receipt", "tokenizer"):
        p.add_argument("--" + name, type=Path)
    a = p.parse_args()
    if not a.execute:
        print(json.dumps({"tasks": TASKS, "seeds": SEEDS, "calls": 16, "paid_calls": 0}))
    elif any(getattr(a, key) is None for key in ("runtime_root", "output", "receipt", "tokenizer")):
        p.error("explicit frozen runtime, fresh root, existing receipt and pinned tokenizer required")
    else:
        execute(a)
