"""Build a local staged SOFTWARE review packet. Never publishes or submits."""
import argparse
from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("repair_paths", ROOT / "scripts/audit-software-repair-paths.py")
PATHS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATHS)
SOURCE = "0b8ccc3ca70a67fed5fc5837b69022261cc60497"
IMAGE = "ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:9455e57ef88fe99d94a0f0b32651c1f52472f9aba6da68c11a68db18c936ed22"
PROFILES = (("software_repair-ignore-d3", 1900000),
            ("software_repair-ignore-d4", 2000000),
            ("software_repair-ignore-d2", 2100000))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def request():
    value = json.loads((ROOT / "config/software-staged-request-template-20261027.json").read_text())
    value.update(submission_id="decision-ledger-software-staged-v12-20261027",
                 name="Decision Ledger: staged software implementation",
                 image=IMAGE,
                 source="https://github.com/nicholas-ruest/openenv-decision-ledger/tree/" + SOURCE)
    value["tasks"] = [{**value["tasks"][0], "task_id": task} for task, _ in PROFILES]
    return value


def fixture(task_id, seed, split):
    task = PATHS.make_task(task_id, seed)
    baseline = PATHS.measure(task, task.initial_source, task.hidden)
    reference = PATHS.measure(task, task.reference_source, task.public + task.hidden)
    if baseline["errors"] or reference["errors"]:
        raise ValueError("native control execution failure")
    if baseline["passed"] >= len(task.hidden) or reference["passed"] != len(task.public + task.hidden):
        raise ValueError("native positive/negative control failure")
    suite = json.dumps([asdict(c) for c in task.hidden], sort_keys=True).encode()
    row = {"task_id": task_id, "seed": seed, "split": split,
           "entrypoint": task.entrypoint, "instructions": task.instructions,
           "initial_source": task.initial_source,
           "public_examples": [asdict(c) for c in task.public],
           "hidden_suite_sha256": digest(suite),
           "initial_source_sha256": digest(task.initial_source.encode()),
           "kind": "procedural_fixture_not_captured_reset_observation"}
    return row, reference["passed"]


def build(output):
    output.mkdir(exist_ok=False)
    names = ("train", "validation", "test")
    suites, identities, total, checks = set(), set(), 0, 0
    family_counts = {}
    streams = {name: (output / (name + ".jsonl")).open("x") for name in names}
    try:
        for task_id, start in PROFILES:
            family_counts[task_id] = 0
            for split, offset, count in (("train", 0, 128), ("validation", 10000, 32), ("test", 20000, 64)):
                for seed in range(start + offset, start + offset + count):
                    row, passed = fixture(task_id, seed, split)
                    identity = (task_id, seed)
                    if identity in identities or row["hidden_suite_sha256"] in suites:
                        raise ValueError("duplicate fixture or hidden suite")
                    identities.add(identity)
                    suites.add(row["hidden_suite_sha256"])
                    streams[split].write(json.dumps(row, sort_keys=True) + "\n")
                    total += 1
                    checks += passed
                    family_counts[task_id] += 1
            (output / "progress.json").write_text(json.dumps({"rows": total, "model_calls": 0}))
    finally:
        for stream in streams.values():
            stream.close()
    (output / "submission-candidate.json").write_text(json.dumps(request(), indent=2) + "\n")
    source_files = sorted((ROOT / "integrations/software-repair/repair_env").glob("*.py")) + [
        ROOT / "integrations/software-repair/Dockerfile.direct",
        ROOT / "integrations/openenv-arena/requirements.lock"]
    source_hashes = {}
    with zipfile.ZipFile(output / "environment-source.zip", "x") as archive:
        for path in source_files:
            if path.is_symlink() or not path.is_file():
                raise ValueError("regular source files required")
            name = str(path.relative_to(ROOT))
            data = path.read_bytes()
            source_hashes[name] = digest(data)
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            archive.writestr(entry, data)
    (output / "README.md").write_text("---\nlicense: mit\ntask_categories:\n- reinforcement-learning\n---\n\n"
        "# Staged software implementation candidate\n\n"
        "Three interleaved ignore-rule tasks: implement aggregation with rule matching supplied; "
        "implement rule matching with aggregation supplied; implement both. These are prerequisite "
        "scaffolds, not increasing difficulty labels or a temporal curriculum. Equal scheduling. "
        "Independent full-contract grading and original limits remain. 384 train, 96 validation and "
        "192 test fixtures with disjoint procedural seeds. Runtime generates fresh episodes rather "
        "than loading these exported fixtures. Rows are procedural fixtures, not captured observations. "
        "Native controls and oracle mutants are not model solves. Reward variation, learning and "
        "private transfer are unconfirmed. No ranking improvement is claimed.\n")
    allow = ("README.md", "environment-source.zip", "submission-candidate.json", "train.jsonl", "validation.jsonl", "test.jsonl")
    manifest = {name: digest((output / name).read_bytes()) for name in allow}
    review = {"approved": False, "submitted": False, "model_calls": 0, "source": SOURCE,
              "image": IMAGE, "rows": total, "unique_hidden_suites": len(suites),
              "oracle_reference_checks": checks, "family_counts": family_counts,
              "source_file_sha256": source_hashes, "manifest": manifest,
              "request_sha256": manifest["submission-candidate.json"],
              "ci": 40471693914, "ci_tests": 638, "anonymous_direct_controls": 260,
              "success_criteria": {"overall_solved_min": 5, "software_solved_min": 1},
              "limits": ["No confirmed model rollout variance or held-out transfer.",
                         "Arena retains trained weights; no local trained-vs-base test.",
                         "One private evaluation draw is noisy.",
                         "Public dataset replacement and new Arena POST require exact-request approval."]}
    (output / "REVIEW.json").write_text(json.dumps(review, indent=2) + "\n")
    return review


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.output)))
