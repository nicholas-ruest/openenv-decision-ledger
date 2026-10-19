"""Build an offline, revision-bound review bundle. No upload or submission code."""

import argparse
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys
import zipfile

from jsonschema import Draft202012Validator


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ci-run", type=int, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()

    def git(*arguments):
        return subprocess.check_output(["git", "-C", str(root), *arguments]).decode().strip()

    if git("rev-parse", "HEAD") != args.revision:
        raise ValueError("source revision mismatch")
    if git("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("tracked runtime source is dirty")
    export = root / "integrations/software-repair/scripts/export_dataset.py"
    subprocess.run([sys.executable, str(export), "--image", args.image,
                    "--output", str(args.output)], check=True)
    output = args.output.resolve()
    runtime = runpy.run_path(str(export))
    request_path = output / "submission-candidate.json"
    request = json.loads(request_path.read_text())
    request["source"] += "/tree/" + args.revision
    schema = request["schema"]
    for item in schema.values():
        Draft202012Validator.check_schema(item)
    validator = Draft202012Validator(schema["action"])
    for action in request["example_actions"] + [request["finish_action"]]:
        validator.validate(action)
    expected_ids = runtime["TRAINING_TASK_IDS"]
    if [task["task_id"] for task in request["tasks"]] != expected_ids:
        raise ValueError("training mix differs")
    rows = [json.loads(line) for line in (output / "tasks.jsonl").read_text().splitlines()]
    identities = {(row["task_id"], row["seed"]) for row in rows}
    if len(rows) != 128 or len(identities) != 128:
        raise ValueError("task export identity collision or unexpected size")
    for row in rows:
        task = runtime["make_task"](row["task_id"], row["seed"])
        if row["files"] != runtime["visible_files"](task):
            raise ValueError("workspace differs from validated source")
    request_path.write_text(json.dumps(request, indent=2) + "\n")
    archive = output / "environment-source.zip"
    paths = ["integrations/software-repair/repair_env",
             "integrations/software-repair/Dockerfile",
             "integrations/software-repair/openenv.yaml",
             "integrations/software-repair/README.md",
             "integrations/openenv-arena/requirements.lock", "LICENSE", "THIRD_PARTY.md"]
    subprocess.run(["git", "-C", str(root), "archive", "--format=zip",
                    "--output=" + str(archive), args.revision, *paths], check=True)
    with zipfile.ZipFile(archive) as package:
        packaged = {name: hashlib.sha256(package.read(name)).hexdigest()
                    for name in package.namelist() if not name.endswith("/")}
    review = {
        "submitted": False, "approval_required": True, "ready_for_submission": False,
        "technical_bundle_prepared": True, "learning_signal_confirmed": False,
        "target_model_calibrated": False, "native_controls_are_model_solves": False,
        "dataset_publication_receipt": "Verify the separate immutable revision receipt.",
        "private_arena_score": None,
        "limitations": ["Eight-task mix remains provisional; diagnostics excluded.",
                        "No confirmed learning or ranking improvement.",
                        "Hosted checkpoint/thinking/Arena wrapper equivalence unattested.",
                        "Approval and a fresh exact-request review are required before submission."],
    }
    (output / "REVIEW.json").write_text(json.dumps(review, indent=2) + "\n")
    with (output / "README.md").open("a") as stream:
        stream.write("\n## Frozen candidate for review\n\n"
                     f"Runtime source: https://github.com/nicholas-ruest/openenv-decision-ledger/tree/{args.revision}\n\n"
                     f"Public amd64 image: `{args.image}`\n\n"
                     f"Native validation: https://github.com/nicholas-ruest/openenv-decision-ledger/actions/runs/{args.ci_run}\n\n"
                     "The complete public examples use compact Python literals; inputs, expectations, "
                     "types, rewards and interpreter limits are preserved. Focused example reads are also "
                     "available as `tests/test_public.py#case=N` for N=1..6.\n\n"
                     "This folder supersedes the earlier software-repair preview. Root-level dataset files "
                     "and historical pinned revisions are separate baseline artifacts. This candidate has "
                     "not been submitted or approved. Native reference controls are not model solves.\n")
    manifest = {
        "runtime_source": args.revision, "image": args.image, "platform": "linux/amd64",
        "ci_run": args.ci_run, "task_rows": len(rows), "task_ids": expected_ids,
        "schema_sha256": hashlib.sha256(canonical(schema)).hexdigest(),
        "schema_origin": "Action/observation classes from the CI-validated runtime revision.",
        "files_sha256": {path.name: sha256(path) for path in output.iterdir() if path.is_file()},
        "packaged_source_files_sha256": packaged,
        "submitted": False, "approval_required": True,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"task_rows": len(rows), "task_ids": len(expected_ids),
                      "schema_sha256": manifest["schema_sha256"],
                      "request_sha256": manifest["files_sha256"]["submission-candidate.json"],
                      "archive_sha256": manifest["files_sha256"]["environment-source.zip"],
                      "submitted": False}))


if __name__ == "__main__":
    main()
