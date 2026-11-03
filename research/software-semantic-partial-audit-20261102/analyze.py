"""Posthoc factorial diagnosis of one retained semantic partial, public examples only.

Submitted code is AST-transformed and interpreted by the pinned Native Program.
It is never executed by host Python. This script does not generate task cases.
"""
import argparse
import ast
import copy
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys

ORIGINAL = "4d69e68c55715d32699f155f068b38a77b8d6d8f"


def name(node, value):
    return isinstance(node, ast.Name) and node.id == value


def edits(source, retain_text=False, implicit_directory=False, parent_block=False):
    """Apply narrowly recognized entrypoint edits; refuse an unfamiliar shape."""
    tree = ast.parse(source)
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    entries = [n for n in functions if n.name == "classify_ignore"]
    if len(entries) != 1:
        raise ValueError("one original entrypoint required")
    entry = entries[0]
    helpers = {n.name: ast.dump(n) for n in functions if n is not entry}
    if retain_text:
        changed = [0, 0]

        class RawRule(ast.NodeTransformer):
            def visit_Call(self, node):
                self.generic_visit(node)
                if (isinstance(node.func, ast.Attribute) and name(node.func.value, "rules")
                        and node.func.attr == "append" and len(node.args) == 1
                        and name(node.args[0], "parsed")):
                    node.args[0] = ast.Name(id="line", ctx=ast.Load())
                    changed[0] += 1
                if (name(node.func, "rule_mode") and len(node.args) == 3
                        and isinstance(node.args[0], ast.Subscript)
                        and name(node.args[0].value, "rule")
                        and isinstance(node.args[0].slice, ast.Constant)
                        and node.args[0].slice.value == 0):
                    node.args[0] = ast.Name(id="rule", ctx=ast.Load())
                    changed[1] += 1
                return node

        RawRule().visit(entry)
        if changed != [1, 1]:
            raise ValueError("unique normalized-text call boundary required")
    if implicit_directory:
        loops = [n for n in entry.body if isinstance(n, ast.For)
                 and name(n.target, "path") and name(n.iter, "paths")]
        if len(loops) != 1:
            raise ValueError("unique own-status path loop required")
        first = loops[0].body[0]
        if not (isinstance(first, ast.Assign) and len(first.targets) == 1
                and name(first.targets[0], "is_dir")
                and isinstance(first.value, ast.Constant) and first.value.value is False):
            raise ValueError("original implicit-directory default required")
        first.value = ast.Constant(value=True)
    if parent_block:
        loops = [n for n in entry.body if isinstance(n, ast.For)
                 and name(n.target, "entry") and name(n.iter, "entries")]
        if not loops:
            raise ValueError("original result loop required")
        loop = loops[-1]
        branch = loop.body[-1]
        if not (isinstance(branch, ast.If) and len(branch.orelse) == 1
                and isinstance(branch.orelse[0], ast.If)):
            raise ValueError("original direct-result branches required")
        inherited = branch.orelse[0].orelse
        if not (len(inherited) == 4 and isinstance(inherited[1], ast.Assign)
                and name(inherited[1].targets[0], "blocked")
                and isinstance(inherited[2], ast.For)
                and isinstance(inherited[-1], ast.Assign)
                and name(inherited[-1].value, "blocked")):
            raise ValueError("original ancestor-only fallback required")
        assignment = copy.deepcopy(inherited[-1])
        assignment.value = ast.BoolOp(op=ast.Or(), values=[
            ast.Name(id="blocked", ctx=ast.Load()),
            ast.Compare(left=ast.Subscript(value=ast.Name(id="own_status", ctx=ast.Load()),
                                          slice=ast.Name(id="path", ctx=ast.Load()), ctx=ast.Load()),
                        ops=[ast.Eq()], comparators=[ast.Constant(value=1)])])
        loop.body[-1:] = copy.deepcopy(inherited[:-1]) + [assignment]
    if {n.name: ast.dump(n) for n in functions if n is not entry} != helpers:
        raise ValueError("working helpers changed")
    return ast.unparse(ast.fix_missing_locations(tree)) + "\n"


def analyze(archive, runtime, arm, sample):
    archive = Path(archive).resolve()
    runtime = Path(runtime).resolve()
    if (subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=runtime, text=True).strip() != ORIGINAL
            or subprocess.check_output(["git", "status", "--porcelain"], cwd=runtime, text=True).strip()):
        raise ValueError("exact clean original Native source required")
    sys.path.insert(0, str(runtime / "integrations/software-repair"))
    from repair_env.runner import Program
    from repair_env.environment import exact
    snapshots = {}

    def read(path, lines=False):
        raw = path.read_bytes()
        snapshots[path] = hashlib.sha256(raw).hexdigest()
        return [json.loads(x) for x in raw.splitlines() if x.strip()] if lines else json.loads(raw)

    closed = read(archive / "closure-proof.json")
    frozen = read(archive / "frozen-confirmation.json")
    records = read(archive / "assessment.verified-records.json")
    if closed.get("assigned") != 8 or closed.get("all_workers_stopped") is not True or frozen.get("source") != ORIGINAL or len(records) != 8:
        raise ValueError("original closed eight-assignment confirmation required")
    selected = [r for r in records if r["arm"] == arm and r["sample"] == sample]
    if len(selected) != 1 or selected[0]["category"] != "partial":
        raise ValueError("one originally recorded semantic partial required")
    record = selected[0]
    captured = []
    for path in sorted(archive.glob("chunk*/live/records.jsonl")):
        local = read(path, True)
        if not any(r["attempt_id"] == record["attempt_id"] for r in local):
            continue
        if sum(r == record for r in local) != 1 or read(path.parents[1] / "launch.json").get("source") != ORIGINAL:
            raise ValueError("original record and launch source required")
        events = read(path.with_name("events.jsonl"), True)
        replies = [e["response"] for e in events if e["event"] == "response" and e["attempt_id"] == record["attempt_id"]]
        if len(replies) != 2 or any(r["choices"][0]["finish_reason"] != "stop" for r in replies):
            raise ValueError("two completed original replies required")
        if [hashlib.sha256(r["id"].encode()).hexdigest() for r in replies] != record["response_ids"]:
            raise ValueError("original response identities required")
        inputs = read(path.parents[1] / "inputs.json")
        groups = [g for g in inputs["confirmation_groups"] if g["task_id"] == record["task_id"] and g["seed"] == record["seed"]]
        if len(groups) != 1:
            raise ValueError("one original input group required")
        observation = json.loads(groups[0]["arms"][arm]["messages"][1]["content"])
        if len(observation["examples"]) > 16000:
            raise ValueError("public example bound")
        examples = ast.literal_eval(observation["examples"])
        if len(examples) != 6:
            raise ValueError("six saved public examples required")
        codes = [json.loads(r["choices"][0]["message"]["content"]).get("content", "") for r in replies]
        source = next((s for s in reversed(codes) if s), observation["source"])
        Program(source)  # Original semantic partial must compile without a correction.
        captured.append((source, examples))
    if len(captured) != 1:
        raise ValueError("one original saved program required")
    source, examples = captured[0]
    variants = []
    for flags in itertools.product((False, True), repeat=3):
        code = source if not any(flags) else edits(source, *flags)
        program = Program(code)
        rows = []
        for index, (args, expected) in enumerate(examples, 1):
            try:
                actual = program.run("classify_ignore", copy.deepcopy(args))
                rows.append({"example": index, "passes": exact(actual, expected)})
            except Exception as exc:
                rows.append({"example": index, "passes": False, "error": type(exc).__name__ + ": " + str(exc)})
        variants.append({"retain_rule_text": flags[0], "implicit_directory": flags[1], "parent_block": flags[2],
                         "public_passes": sum(r["passes"] for r in rows), "rows": rows,
                         "program_sha256": hashlib.sha256(code.encode()).hexdigest()})
    if any(hashlib.sha256(p.read_bytes()).hexdigest() != h for p, h in snapshots.items()):
        raise ValueError("retained archive changed during analysis")
    return {"kind": "retained_semantic_partial_factorial", "runtime_source": ORIGINAL,
            "variants": variants, "retained_programs": 1, "underlying_cases": 1,
            "public_examples_per_program": 6, "archive_files_sha256": {str(p): h for p, h in snapshots.items()},
            "working_helpers_unchanged": True, "serving_source_changed": False,
            "public_examples_only": True, "hidden_access": False, "posthoc": True,
            "original_classification_changed": False, "new_model_calls": 0, "new_cases": 0,
            "model_improvement": False, "is_training": False, "actual_metaharness_executed": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--sample", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("fresh private output required")
    result = analyze(args.archive, args.runtime, args.arm, args.sample)
    with args.output.open("x") as output:
        json.dump(result, output, indent=2)
        output.write("\n")
    print(json.dumps({"variants": [{k: v[k] for k in ("retain_rule_text", "implicit_directory", "parent_block", "public_passes")} for v in result["variants"]], "new_model_calls": 0}))
