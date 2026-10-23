"""Offline audit of unchanged tasks with explicitly versioned runtime surfaces.

No upload, credential access, inference or Arena operation exists here.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

OLD = 'c95e6fe79e44c9b1514fd59e186a0a70ac424858'
CURRENT = '43b548debcb469af196a282bad07fc3bd8d33b15'
PUBLIC_TASKS_SHA = 'd197b7ffe06f8a2913d2cdf38943fb4b858a1c3e3200ab9971edc8e2faca2b64'


def typed(value):
    kind = type(value)
    if value is None:
        return ['none']
    if kind in (bool, int, str):
        return [kind.__name__, value]
    if kind is float:
        if not math.isfinite(value):
            raise ValueError('nonfinite fixture')
        return ['float', value]
    if kind in (list, tuple):
        return [kind.__name__, [typed(item) for item in value]]
    if kind is dict:
        return ['dict', [[typed(key), typed(item)] for key, item in value.items()]]
    raise TypeError('unexpected fixture type')


def digest(value):
    return hashlib.sha256(json.dumps(typed(value), ensure_ascii=True, separators=(',', ':')).encode()).hexdigest()


def collect(root, public_path):
    sys.path.insert(0, str(Path(root) / 'integrations/software-repair'))
    from repair_env.tasks import make_task, visible_files
    rows = [json.loads(line) for line in Path(public_path).read_text().splitlines()]
    if len(rows) != 128 or len({(r['task_id'], r['seed']) for r in rows}) != 128:
        raise ValueError('expected 128 unique published fixtures')
    content = {}
    counts = {'rows': 128, 'exact_visible_files': 0, 'exact_instructions': 0,
              'exact_initial_source': 0, 'exact_readme': 0, 'exact_test_rendering': 0}
    for row in rows:
        task = make_task(row['task_id'], row['seed'])
        files = visible_files(task)
        counts['exact_visible_files'] += row['files'] == files
        counts['exact_instructions'] += row['prompt'] == task.instructions
        counts['exact_initial_source'] += row['files']['src/solution.py'] == task.initial_source
        counts['exact_readme'] += row['files']['README.md'] == files['README.md']
        counts['exact_test_rendering'] += row['files']['tests/test_public.py'] == files['tests/test_public.py']
        data = {'entrypoint': task.entrypoint, 'instructions': task.instructions,
                'initial': task.initial_source, 'reference': task.reference_source,
                'public': [(case.args, case.expected) for case in task.public],
                'hidden': [(case.args, case.expected) for case in task.hidden]}
        content[row['task_id'] + '|' + str(row['seed'])] = digest(data)
    return {'counts': counts, 'typed_task_hashes': content}


def checked_root(path, revision):
    root = path.resolve()
    actual = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain', '--untracked-files=no'], text=True)
    if actual != revision or dirty:
        raise ValueError('clean pinned source checkout required')
    return root


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--old-root', type=Path)
    parser.add_argument('--current-root', type=Path)
    parser.add_argument('--public-tasks', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--collect', type=Path)
    args = parser.parse_args()
    if args.collect is not None:
        print(json.dumps(collect(args.collect, args.public_tasks)))
        return
    if not args.old_root or not args.current_root or not args.output:
        raise ValueError('both pinned checkouts and fresh output required')
    if args.output.exists():
        raise ValueError('refusing to overwrite parity evidence')
    if args.public_tasks.stat().st_size > 4_000_000:
        raise ValueError('public task file exceeds size bound')
    raw = args.public_tasks.read_bytes()
    if len(raw) > 4_000_000 or hashlib.sha256(raw).hexdigest() != PUBLIC_TASKS_SHA:
        raise ValueError('pinned public task bytes differ')
    roots = [checked_root(args.old_root, OLD), checked_root(args.current_root, CURRENT)]
    values = []
    for root in roots:
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--collect', str(root),
                                 '--public-tasks', str(args.public_tasks.resolve())],
                                check=True, capture_output=True, text=True, timeout=60)
        values.append(json.loads(result.stdout))
    old, current = values
    if old['counts']['exact_visible_files'] != 128:
        raise ValueError('published fixture/source correspondence failed')
    same_keys = set(old['typed_task_hashes']) == set(current['typed_task_hashes'])
    matches = sum(value == current['typed_task_hashes'].get(key) for key, value in old['typed_task_hashes'].items())
    report = {'old_source': OLD, 'current_runtime_source': CURRENT,
        'dataset': 'GlobalBusinessAdvisors/openenv-decision-ledger',
        'dataset_revision': '063900b75ac26423166a80d11e814092b1d05627',
        'public_tasks_sha256': PUBLIC_TASKS_SHA, 'task_instances': 128,
        'same_task_seed_keys': same_keys, 'exact_typed_task_content_matches': matches,
        'old_source_alignment': old['counts'], 'current_runtime_alignment': current['counts'],
        'source_archive_matches_current_runtime': False,
        'workspace_interface_and_documentation_differ': True,
        'interpretation': 'Public task content is unchanged; the historical runtime archive, action interface and workspace rendering must not be described as the current runtime.',
        'is_learning_evidence': False, 'is_submission_approval': False,
        'new_model_calls': 0, 'submitted': False}
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
