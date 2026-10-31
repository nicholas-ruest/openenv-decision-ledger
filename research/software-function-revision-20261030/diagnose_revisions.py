"""Posthoc aggregate repair/retention audit. Never sends model requests."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--expected-source', required=True)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    assert subprocess.check_output(['git', '-C', str(a.source), 'rev-parse', 'HEAD'], text=True).strip() == a.expected_source
    subprocess.run(['git', '-C', str(a.source), 'diff', '--quiet', 'HEAD'], check=True)
    sys.path.insert(0, str(a.source / 'research/software-function-revision-20261030'))
    import assemble
    from repair_env.runner import Program, Rejected
    from repair_env.environment import check
    from repair_env.tasks import SOURCE_PATH

    def measure(trial):
        core = trial.env._direct._core
        source = core._files[SOURCE_PATH]
        try:
            program = Program(source)
            public = check(program, core._task, core._task.public)[0]
            hidden = check(program, core._task, core._task.hidden)[0]
            fingerprint = hashlib.sha256(ast.dump(ast.parse(source), include_attributes=False).encode()).hexdigest()
            return dict(public_exact=public, hidden_exact=hidden, ast_sha256=fingerprint)
        except (Rejected, SyntaxError, RecursionError):
            return dict(public_exact=None, hidden_exact=None, ast_sha256=None)

    rows, provenance = [], []
    for index in range(4):
        live = a.archive / f'chunk{index}/live'
        if not (live / 'complete.json').exists():
            continue
        raw = (live / 'events.jsonl').read_bytes()
        events = [json.loads(line) for line in raw.splitlines()]
        records = [json.loads(line) for line in (live / 'records.jsonl').read_text().splitlines()]
        provenance.append(dict(chunk=index, events_sha256=hashlib.sha256(raw).hexdigest()))
        for job, record in zip(assemble.protocol.bundle(index)['screen_jobs'], records):
            assert job['attempt_id'] == record['attempt_id']
            trial, stages, modes = assemble.protocol.Trial(job), [], []
            for event in events:
                if event['event'] != 'response' or event['attempt_id'] != job['attempt_id']:
                    continue
                choice = event['response']['choices'][0]
                if choice['finish_reason'] != 'stop' or trial.closed:
                    break
                text = choice['message'].get('content')
                try:
                    value = json.loads(text)
                    modes.append(value.get('mode', 'module') if isinstance(value, dict) else None)
                except (TypeError, ValueError):
                    modes.append(None)
                result = trial.consume(text)
                if result['category'] == 'format':
                    break
                stages.append(measure(trial))
            first, final = (stages[0], stages[-1]) if stages else (None, None)
            rows.append(dict(attempt_id=job['attempt_id'], arm=job['arm'], sample=job['sample'], category=record['category'], stages=stages, action_modes=modes, applied_function_revision=trial.env._applied_function_revision, first_full=first is not None and first['hidden_exact'] == 30, final_full=record['category'] == 'full', revision_added_full=first is not None and first['hidden_exact'] is not None and first['hidden_exact'] < 30 and record['category'] == 'full', revision_changed_ast=len(stages) == 2 and first['ast_sha256'] != final['ast_sha256']))
    result = dict(source=a.expected_source, posthoc=True, model_calls=0, observations_or_requests_changed=False, assigned_attempts=8, completed_attempts=len(rows), public_cases_per_attempt=6, hidden_cases_per_attempt=30, provenance=provenance, rows=rows, limitations='Aggregate posthoc analysis only. No hidden cases, source, output keys or reasoning exported. First proposals were not randomized between review arms. A retained full first proposal is not a repair gained from revision.')
    with a.output.open('x') as f:
        json.dump(result, f, indent=2)
    print(json.dumps(dict(completed_attempts=len(rows), revision_added_full=sum(r['revision_added_full'] for r in rows))))


if __name__ == '__main__':
    main()
