"""Describe reported trainer metrics; never infer actor stop reasons/task names."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import statistics


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def describe(rows):
    clean = [r for r in rows if r['step/retries'] == 0]
    full = lambda r: r['completions/clipped_ratio'] == 1
    saturated = lambda r: r['reward'] == 1 and r['reward_std'] == 0
    varied = lambda r: r['reward_std'] > 0 and r['grad_norm'] > 0
    return dict(
        recorded_updates=len(rows), zero_retry_updates=len(clean),
        reported_clipped_ratio_counts={str(k): v for k, v in sorted(Counter(
            r['completions/clipped_ratio'] for r in rows).items())},
        mean_reported_clipped_ratio=statistics.mean(r['completions/clipped_ratio'] for r in rows),
        reported_max_completion_length_range=[min(r['completions/max_length'] for r in rows),
                                               max(r['completions/max_length'] for r in rows)],
        positive_reported_max_terminated_length_updates=sum(
            r['completions/max_terminated_length'] > 0 for r in rows),
        zero_retry_full_reported_clipping_updates=sum(full(r) for r in clean),
        zero_retry_saturated_updates=sum(saturated(r) for r in clean),
        zero_retry_saturated_and_full_reported_clipping_updates=sum(
            saturated(r) and full(r) for r in clean),
        zero_retry_nonzero_std_and_gradient_updates=sum(varied(r) for r in clean),
        zero_retry_nonzero_std_and_gradient_and_full_reported_clipping_updates=sum(
            varied(r) and full(r) for r in clean))


def analyze(summary, logs):
    if summary.get('run') != 'a3274296c46341a847407f97' or summary.get('num_logs') != len(logs):
        raise ValueError('exact actual run/count binding required')
    seen = set(); groups = {}
    fields = ('step/task', 'step/retries', 'reward', 'reward_std', 'grad_norm',
              'completions/clipped_ratio', 'completions/max_length',
              'completions/max_terminated_length')
    for row in logs:
        step = row['step']
        if type(step) is not int or step in seen:
            raise ValueError('unique actual optimizer steps required')
        seen.add(step)
        if any(type(row.get(k)) not in (int, float) or not math.isfinite(row[k]) for k in fields):
            raise ValueError('finite recorded metrics required')
        task = row['step/task']
        if task < 1 or int(task) != task or not 0 <= row['completions/clipped_ratio'] <= 1:
            raise ValueError('recorded numeric task and clipped ratio required')
        groups.setdefault(str(int(task)), []).append(row)
    if not logs:
        raise ValueError('no observed updates')
    return dict(run=summary['run'], raw_logs_sha256=digest(logs),
                optimizer_steps=[min(seen), max(seen)], aggregate=describe(logs),
                numeric_groups={k: describe(v) for k, v in sorted(groups.items())},
                task_names_attested=False, stop_reason_semantics_attested=False,
                actor_token_limit_attested=False, causal_explanation_established=False,
                new_model_calls=0, new_training=False, leaderboard_gain=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--logs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(json.loads(args.summary.read_text()), json.loads(args.logs.read_text()))
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
