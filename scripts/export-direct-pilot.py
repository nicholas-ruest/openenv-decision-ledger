"""Prepare an immutable one-task Arena review bundle; no network or submission.

Oracle controls are not model solves. Public publication and explicit human
approval remain separate prerequisites. Never accepts or reads credentials.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "integrations/software-repair"))
from repair_env.direct_environment import DirectRepairAction, DirectRepairObservation, DirectRepairEnvironment, KV_TASK_IDS
from repair_env.environment import check
from repair_env.runner import Program
from repair_env.tasks import make_task, task_fingerprint

DATASET = "GlobalBusinessAdvisors/openenv-decision-ledger"
TARGET_TASK = KV_TASK_IDS[1]
SPLITS = {"train": (1160000, 128), "validation": (1170000, 32), "test": (1180000, 64)}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def request(image, source):
    if not re.fullmatch(r"ghcr\.io/nicholas-ruest/openenv-decision-ledger@sha256:[0-9a-f]{64}", image):
        raise ValueError("immutable owned image digest required")
    if not re.fullmatch(r"[0-9a-f]{40}", source):
        raise ValueError("frozen public runtime source required")
    return {"submission_id": "decision-ledger-kv-repair-v6-20261022",
        "name": "Decision Ledger: transactional software repair",
        "image": image,
        "source": "https://github.com/nicholas-ruest/openenv-decision-ledger/tree/" + source,
        "dataset": DATASET,
        "schema": {"action": DirectRepairAction.model_json_schema(),
                   "observation": DirectRepairObservation.model_json_schema()},
        "tasks": [{"task_id": TARGET_TASK, "split": "train",
            "reset_wall_s": 120, "rollout_wall_s": 600, "verifier_wall_s": 30,
            "tool_wall_s": 20, "tool_calls_total": 1, "tool_calls_per_minute": 60,
            "completion_tokens": 8192, "context_tokens": 24576,
            "cpu_floor_vcpus": 1, "memory_gib": 2, "workspace_gib": 2}],
        "example_actions": [{"content": ""}], "finish_action": {"content": ""}}


def export(output, image, source):
    value = request(image, source)
    output.mkdir(exist_ok=False)
    seen, source_hashes = set(), set()
    count = controls = 0
    for split, (start, size) in SPLITS.items():
        with (output / (split + ".jsonl")).open("x") as stream:
            for seed in range(start, start + size):
                assert seed not in seen; seen.add(seed)
                task = make_task(TARGET_TASK, seed)
                before, failed = check(Program(task.initial_source), task, task.hidden, details=True)
                after, passed = check(Program(task.reference_source), task, task.public + task.hidden, details=True)
                assert before < len(task.hidden) and after == len(task.public + task.hidden)
                assert not any(x["error"] for x in failed + passed)
                env = DirectRepairEnvironment(); obs = env.reset(task_id=task.task_id, seed=seed)
                rendered = obs.model_dump_json()
                key = digest(rendered.encode()); assert key not in source_hashes; source_hashes.add(key)
                row = {"task_id": task.task_id, "split": split, "seed": seed,
                       "reset_observation_json": rendered, "observation_sha256": key,
                       "task_fingerprint": task_fingerprint(task)}
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                count += 1; controls += after
    body = (json.dumps(value, indent=2) + "\n").encode()
    (output / "submission-candidate.json").write_bytes(body)
    allow = sorted((ROOT / "integrations/software-repair/repair_env").glob("*.py")) + [
        ROOT / "integrations/software-repair/Dockerfile.direct",
        ROOT / "integrations/openenv-arena/requirements.lock",
        ROOT / "docs/software-kv-pilot-2026-10-22.md"]
    with zipfile.ZipFile(output / "environment-source.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in allow:
            assert path.is_file() and not path.is_symlink()
            archive.write(path, path.relative_to(ROOT))
    (output / "README.md").write_text("---\nlicense: mit\ntask_categories:\n- reinforcement-learning\nconfigs:\n- config_name: kv_repair_v6\n  data_files:\n  - split: train\n    path: train.jsonl\n  - split: validation\n    path: validation.jsonl\n  - split: test\n    path: test.jsonl\n---\n\n# Transactional software repair candidate\n\n"
        "Repair a versioned key/value command processor: atomic rollback, idempotency, tombstones, sequential checks and audit records. "
        "One code response is scored by the bounded interpreter against independently generated hidden cases. "
        "No imports, host execution or private benchmark data. The initial module has seeded semantic defects. "
        "Partial reward requires improving meaningful exact result fields over that module; full credit requires every "
        "hidden case. Unchanged, cosmetic and non-improving code earns zero.\n\n"
        "The environment image executes the generator, not these public fixture rows. Public/hidden inputs "
        "are independently generated and disjoint. The three exported procedural seed splits are disjoint. "
        "Source revision: " + source + ". This is a separate candidate from the historical eight-task "
        "interactive preview. It has not been submitted, trained or shown to improve rankings.\n")
    manifest = {p.name: digest(p.read_bytes()) for p in sorted(output.iterdir()) if p.is_file()}
    report = {"source": source, "image": image, "task": TARGET_TASK,
        "rows": count, "unique_observations": len(source_hashes), "oracle_reference_cases_passed": controls,
        "baseline_has_semantic_defects": True, "candidate_execution_errors": 0,
        "splits": SPLITS, "manifest": manifest, "request_sha256": digest(body),
        "public_matching_dataset_publication_required": True,
        "approved": False, "submitted": False, "trained": False,
        "model_calls": 0, "learning_or_ranking_improvement": False}
    (output / "REVIEW.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--image", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--output", required=True, type=Path); args = p.parse_args()
    print(json.dumps(export(args.output, args.image, args.source)))
