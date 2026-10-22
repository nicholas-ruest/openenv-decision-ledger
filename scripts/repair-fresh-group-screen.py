"""Bounded calibration of fresh-instance groups; never trains or submits.

Unlike the repeated-prompt diagnostic, each five-way group resets five distinct
procedural instances. First four valid completions are selected in observed
completion order. Conservative failure exclusions and hosted-model equivalence
remain explicit limitations; this is not an attested Arena trainer replica.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import threading
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("frozen_repair_screen", ROOT / "scripts/repair-signal-screen.py")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)
TASK = "software_repair-kv-d2"
SEEDS = {"screen": [1152000, 1152100], "confirm": [1153000, 1153100]}
CURRICULA = {"kv": (TASK, SEEDS), "linear": ("software_repair-linear-d2",
             {"screen": [1200000,1200100], "confirm": [1201000,1201100]}),
             "linear_synthesis": ("software_repair-linear-d3",
             {"screen":[1202000,1202100],"confirm":[1203000,1203100]}),
             "linear_control": ("software_repair-linear-d4",
             {"screen":[1202000,1202100],"confirm":[1203000,1203100]})}


def plan(stage, curriculum="kv"):
    if curriculum not in CURRICULA:
        raise ValueError("unknown curriculum")
    task, seeds = CURRICULA[curriculum]
    if stage not in seeds:
        raise ValueError("unknown stage")
    return {"stage": stage, "curriculum": curriculum, "groups": [[seed+i for i in range(5)] for seed in seeds[stage]],
            "task_id": task, "max_calls": 10, "samples_per_group": 5,
            "valid_samples_selected": 4, "selection": "first four valid in observed completion order",
            "no_retry": True, "required_productive_groups": 2,
            "is_training": False, "arena_trainer_attested": False,
            "failure_exclusions": "provider/format/truncation/unsupported-code/execution/budget failures are not semantic wrong answers"}


def assess(rows, expected_seeds):
    if len(rows) != len(expected_seeds) or len({r["seed"] for r in rows}) != len(rows) or any(r["seed"] not in expected_seeds for r in rows):
        raise ValueError("duplicate or unexpected procedural instance")
    valid = [r for r in rows if r.get("failure") is None]
    hashes = [r.get("prompt_sha256") for r in valid]
    identities = [c.get("provider_response_id_sha256") for r in valid for c in r.get("calls", [])]
    if any(not h for h in hashes) or len(set(hashes)) != len(hashes):
        raise ValueError("fresh prompt identities missing or duplicated")
    if len(identities) != len(valid) or any(not h for h in identities) or len(set(identities)) != len(identities):
        raise ValueError("independent single-call identities required")
    chosen = valid[:4]
    rewards = [r["reward"] for r in chosen]
    if any(type(r) not in (int, float) or not 0 <= r <= 1 for r in rewards):
        raise ValueError("finite semantic rewards required")
    return {"observed": len(rows), "valid": len(valid), "selected_seeds": [r["seed"] for r in chosen],
            "selected_rewards": rewards, "excluded": [{"seed": r["seed"], "failure": r["failure"]} for r in rows if r.get("failure")],
            "productive": len(chosen) == 4 and any(x == 1 for x in rewards) and any(0 <= x < 1 for x in rewards)}


def independent(records):
    prompts = [r["prompt_sha256"] for r in records if r.get("prompt_sha256")]
    calls = [c for r in records for c in r.get("calls", [])]
    labels = [c.get("client_call_label") for c in calls]
    responses = [c["provider_response_id_sha256"] for c in calls if c.get("provider_response_id_sha256")]
    return (len(prompts) == len(set(prompts)) and all(labels) and len(labels) == len(set(labels))
            and len(responses) == len(set(responses)))


def source_hashes():
    paths = [Path(__file__), ROOT / "scripts/repair-signal-screen.py", ROOT / "scripts/provider_stream.py",
             *sorted((ROOT / "integrations/software-repair/repair_env").glob("*.py")),
             *sorted((ROOT / "integrations/software-repair/scripts").glob("*.py")), base.HELPER]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def verify_screen(directory, curriculum):
    if directory is None:
        raise ValueError("verified productive primary screen required for confirmation")
    protocol = json.loads((directory / "protocol.json").read_text())
    declared = plan("screen", curriculum)
    if any(protocol.get(k) != v for k,v in declared.items()) or protocol.get("source_files_sha256") != source_hashes():
        raise ValueError("primary screen plan or frozen source mismatch")
    rows = [json.loads(x) for x in (directory / "episodes.jsonl").read_text().splitlines() if x]
    if len(rows) != 10 or not independent(rows):
        raise ValueError("primary screen records or identities invalid")
    groups = [assess([r for r in rows if r.get("fresh_group") == i], seeds)
              for i,seeds in enumerate(declared["groups"])]
    saved = json.loads((directory / "complete.json").read_text())
    if not all(g["productive"] for g in groups) or saved.get("groups") != groups or saved.get("signal_gate") is not True:
        raise ValueError("primary screen is not productive in both groups")
    return protocol, rows


def disjoint(left, right):
    for kind in ("prompt_sha256", "client_call_label", "provider_response_id_sha256"):
        def ids(rows):
            return ({r[kind] for r in rows if r.get(kind)} if kind == "prompt_sha256" else
                    {c[kind] for r in rows for c in r.get("calls",[]) if c.get(kind)})
        if not ids(left) or not ids(right) or ids(left)&ids(right):return False
    return True


def execute(deadline, args):
    declared = plan(args.stage, getattr(args,"curriculum","kv"))
    prior_protocol, prior_rows = (verify_screen(getattr(args,"screen",None), declared["curriculum"])
                                  if args.stage == "confirm" else (None, []))
    args.output.mkdir(exist_ok=False)
    budget = base.DollarReservations(args.budget_receipt)
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        raise ValueError("existing private environment required")
    counter = base.helper.load_counter(argparse.Namespace(accounting="arena", tokenizer_json=args.tokenizer,
                                                         tokenizer_sha256=base.TOKENIZER_SHA))
    opener = urllib.request.build_opener(base.helper.NoRedirect(), urllib.request.ProxyHandler({}))
    frozen = base.quote(opener, token, base.request_timeout(deadline, 15, now=base._now()))
    settings = base.get_profile("kv_components", "screen")["sampling_settings"]
    if prior_protocol and (prior_protocol["provider"] != frozen or prior_protocol["sampling_settings"] != settings
                           or prior_protocol["tokenizer_sha256"] != base.TOKENIZER_SHA):
        raise ValueError("confirmation provider, tokenizer or capacity changed")
    protocol = {**declared, "sampling_settings": settings, "provider": frozen,
                "tokenizer_sha256": base.TOKENIZER_SHA,
                "source_files_sha256": source_hashes(),
                "thinking_verified": False, "checkpoint_attested": False}
    (args.output / "protocol.json").write_text(json.dumps(protocol, indent=2))
    stop = threading.Event()
    results, records = [], []
    with (args.output / "episodes.jsonl").open("x") as stream:
        for index, seeds in enumerate(declared["groups"]):
            group = []
            with ThreadPoolExecutor(max_workers=5) as pool:
                futures = [pool.submit(base.episode, declared["task_id"], seed, 0, token, counter, budget, frozen,
                                       stop, deadline, args.output.name, settings) for seed in seeds]
                for future in as_completed(futures):
                    row = future.result()
                    row["fresh_group"] = index
                    group.append(row)
                    records.append(row)
                    stream.write(json.dumps(row) + "\n"); stream.flush(); os.fsync(stream.fileno())
            results.append(assess(group, seeds))
            if stop.is_set():
                break
    separate = not prior_rows or disjoint(prior_rows, records)
    summary = {"groups": results, "unique_prompts": sum(x["observed"] for x in results),
               "independent_sampling_identities": independent(records),
               "independent_from_primary": separate,
               "signal_gate": len(results) == 2 and separate and independent(records) and all(x["productive"] for x in results),
               "confirmation_required": args.stage == "screen", "is_training": False,
               "arena_trainer_attested": False}
    (args.output / "complete.json").write_text(json.dumps(summary, indent=2))


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--execute", action="store_true")
    p.add_argument("--stage", choices=tuple(SEEDS), default="screen")
    p.add_argument("--curriculum", choices=tuple(CURRICULA), default="kv")
    p.add_argument("--screen", type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--budget-receipt", type=Path)
    p.add_argument("--tokenizer", type=Path)
    a = p.parse_args(argv)
    if not a.execute:
        print(json.dumps(plan(a.stage,a.curriculum))); return 0
    if any(x is None for x in (a.output, a.budget_receipt, a.tokenizer)) or a.output.exists():
        raise ValueError("fresh output and existing bounded allocation/tokenizer required")
    if a.stage == "confirm":verify_screen(a.screen,a.curriculum)
    result = base.run_bounded(execute, (a,), 1200, a.output.with_name(a.output.name + ".worker.jsonl"))
    print(json.dumps({"worker": result, "is_training": False}))
    return 0 if result["status"] == "completed" and result["shutdown_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
