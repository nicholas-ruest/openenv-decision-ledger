"""Join public Trackio metrics by exact optimizer step, without inferring task names."""

import argparse
import importlib.util
import json
import math
from pathlib import Path
import statistics


METRICS = ("step/task", "reward", "reward_std", "grad_norm",
           "frac_reward_zero_std", "step/retries", "completions/clipped_ratio")


def index_rows(rows):
    """Reject ambiguous joins rather than keeping the last duplicate."""
    result = {}
    for row in rows:
        step = row.get("step")
        if type(step) is not int or step < 0 or step in result:
            raise ValueError("invalid or duplicate optimizer step")
        value = row.get("value")
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("non-finite or nonnumeric metric")
        result[step] = value
    return result


def analyze(records):
    indexed = {name: index_rows(rows) for name, rows in records.items()}
    task_rows = indexed.get("step/task", {})
    groups = {}
    for step, task in sorted(task_rows.items()):
        if int(task) != task or task < 1:
            raise ValueError("invalid recorded task ID")
        group = groups.setdefault(str(int(task)), [])
        group.append({"step": step, **{name: values[step]
                      for name, values in indexed.items() if step in values}})
    summary = {}
    required = ("reward", "reward_std", "grad_norm", "step/retries")
    for task, rows in groups.items():
        complete = [r for r in rows if all(k in r for k in required)]
        clean = [r for r in complete if r["step/retries"] == 0]
        rewards = [r["reward"] for r in clean]
        summary[task] = {
            "task_name": None,
            "recorded_steps": len(rows),
            "incomplete_steps": len(rows) - len(complete),
            "retried_steps": sum(r["step/retries"] > 0 for r in complete),
            "clean_steps": len(clean),
            "productive_clean_steps": sum(r["reward_std"] > 0 and
                                           r["grad_norm"] > 0 for r in clean),
            "zero_variance_clean_steps": sum(r["reward_std"] == 0 for r in clean),
            "saturated_clean_steps": sum(r["reward"] == 1 and
                                          r["reward_std"] == 0 for r in clean),
            "first10_clean_reward": statistics.mean(rewards[:10]) if rewards else None,
            "last10_clean_reward": statistics.mean(rewards[-10:]) if rewards else None,
            "mean_clean_reward": statistics.mean(rewards) if rewards else None,
        }
    return {
        "groups": summary,
        "task_mapping": "unattested: IDs come from step/task; no rotation inference",
        "unassigned_metric_steps": {
            name: sorted(set(values) - set(task_rows))
            for name, values in indexed.items() if name != "step/task"
        },
        "records": records,
        "limitations": [
            "Productive means nonzero recorded reward std and gradient, not held-out gain.",
            "Retried steps are reported separately; failures without metric rows are unavailable.",
            "Clipping flags do not by themselves prove actual truncation.",
            "Unknown task-name mapping must be resolved before changing family weights.",
        ],
        "model_improvement_claim": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("fresh output required")
    spec = importlib.util.spec_from_file_location(
        "trackio_read", Path(__file__).with_name("analyze-trackio-public.py"))
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    payload = {"project": args.project, "run": args.run, "run_id": args.run}
    summary = reader.read("get_run_summary", payload)
    if (summary.get("config") or {}).get("recipe") == "cpu-dummy-simulation":
        raise ValueError("simulation is not target training")
    records = {name: reader.read("get_metric_values", {**payload, "metric_name": name})
               for name in METRICS if name in summary.get("metrics", [])}
    if "step/task" not in records:
        raise ValueError("task identity unavailable")
    result = {"project": args.project, "run": args.run, **analyze(records)}
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps({k: v for k, v in result.items() if k != "records"}))


if __name__ == "__main__":
    main()
