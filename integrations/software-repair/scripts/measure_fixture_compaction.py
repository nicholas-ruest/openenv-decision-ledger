"""Measure lossless fixture rendering offline using the pinned local tokenizer."""

import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tokenizers import Tokenizer

from repair_env.environment import RepairAction, RepairEnvironment, exact
from repair_env.tasks import TRAINING_TASK_IDS, compact_literal, task_fingerprint

TOKENIZER_SHA = "0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if hashlib.sha256(args.tokenizer.read_bytes()).hexdigest() != TOKENIZER_SHA:
        raise ValueError("tokenizer identity mismatch")
    tokenizer = Tokenizer.from_file(str(args.tokenizer))
    measurements = []
    for task_id in TRAINING_TASK_IDS + ["software_repair-release-d1"]:
        for seed in (1040000, 1040100):
            env = RepairEnvironment()
            env.reset(task_id=task_id, seed=seed)
            observed = env.step(RepairAction(op="read", path="tests/test_public.py"))
            cases = [(case.args, case.expected) for case in env._task.public]
            literal = ast.parse(observed.content).body[2].decorator_list[0].args[1]
            if not exact(ast.literal_eval(literal), cases):
                raise ValueError("public cases changed")
            compact = compact_literal(cases)
            if observed.content.count(compact) != 1:
                raise ValueError("fixture replacement is ambiguous")
            old_content = observed.content.replace(compact, repr(cases), 1)
            old = observed.model_copy(update={"content": old_content})
            measurements.append({
                "task_id": task_id,
                "seed": seed,
                "task_fingerprint": task_fingerprint(env._task),
                "old_observation_tokens": len(tokenizer.encode(old.model_dump_json()).ids),
                "new_observation_tokens": len(tokenizer.encode(observed.model_dump_json()).ids),
                "old_file_bytes": len(old_content.encode()),
                "new_file_bytes": len(observed.content.encode()),
                "public_cases_exact": True,
            })
    report = {
        "date": "2026-10-19",
        "change": "Remove optional Python literal separator whitespace from complete public fixtures.",
        "tokenizer_sha256": TOKENIZER_SHA,
        "measurements": measurements,
        "new_model_calls": 0,
        "is_training": False,
        "schema_changed": False,
        "task_cases_changed": False,
        "interpreter_or_reward_changed": False,
        "default_training_mix_changed": False,
        "live_benefit_measured": False,
        "limitations": [
            "Token counts compare alternative observations on identical task cases.",
            "The old representation is reconstructed by replacing only the fixture literal.",
            "Readability and model success effects require independent evaluation.",
            "This is not evidence of trained-model or leaderboard improvement.",
        ],
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
