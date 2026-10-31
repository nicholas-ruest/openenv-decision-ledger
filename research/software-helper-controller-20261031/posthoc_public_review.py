"""Public-only counterfactual over a completed, independently verified archive.

This neither calls a provider nor finalizes proposals for a hidden grade.
It must run after the original confirmation has closed, in a fresh process.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def review(trial):
    if not trial.native:
        return None
    obs = trial.native[-1]
    if obs['done'] or obs['stage'] != 'revision' or obs['reward'] != 0:
        raise ValueError('only nonterminal public review may be inspected')
    r = json.loads(obs['feedback'])
    if r.get('public_only') is not True or r.get('hidden_access') is not False:
        raise ValueError('public-only review required')
    return {k: r.get(k) for k in ('kind', 'passed', 'total')}


def run(a):
    source = a.source_root.resolve()
    if subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() != a.expected_source:
        raise ValueError('exact original live source required')
    if subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'], text=True).strip():
        raise ValueError('clean original live source required')
    if sha(a.archive/'assessment.json') != a.assessment_sha256:
        raise ValueError('completed independent assessment lease required')
    assessment = json.loads((a.archive/'assessment.json').read_text())
    if assessment.get('attempts') != 8 or assessment.get('all_live_replies_verified') is not True:
        raise ValueError('all original assignments and known replies required')
    sys.path[:0] = [str(source/'research/software-public-pass-confirmation-20261031'),
                     str(source/'integrations/software-repair')]
    import caller
    protocol, _ = caller.modules()
    protocol.configure_gate(a.screen_gate, a.screen_gate_sha256)
    policy = caller.load('exact_public_helper_counterfactual', Path(__file__).with_name('helper_policy.py'))
    rows = []
    for i in range(4):
        c = a.archive/f'chunk{i}'
        bundle = json.loads((c/'inputs.json').read_text())
        proof = json.loads((c/'independent-verification.json').read_text())
        done = json.loads((c/'live/complete.json').read_text())
        if (bundle != protocol.bundle(i) or proof.get('clean_shutdown') is not True
                or proof.get('all_workers_stopped') is not True or done.get('scripted') is not False
                or done.get('assigned_attempts') != 2 or done.get('recorded_attempts') != 2):
            raise ValueError('complete independently replayed original chunk required')
        events = [json.loads(l) for l in (c/'live/events.jsonl').read_text().splitlines()]
        for job in bundle['confirmation_jobs']:
            first = [e for e in events if e['event'] == 'response'
                     and e['attempt_id'] == job['attempt_id'] and e['turn'] == 0]
            if len(first) != 1:
                raise ValueError('one unique original first response required')
            choice = first[0]['response']['choices'][0]
            row = dict(arm=job['arm'], sample=job['sample'], eligible=False)
            if choice.get('finish_reason') != 'stop':
                row['reason'] = 'original_first_response_incomplete'
                rows.append(row)
                continue
            # Extract the unchanged underlying Trial, without the public-pass
            # finalization controller. No hidden finalization is performed.
            original = protocol.Trial(job).policy.trial
            changed = protocol.Trial(job).policy.trial
            if original.messages != changed.messages:
                raise ValueError('same original public problem required')
            text = choice['message']['content']
            before = original.consume(text)
            controller = policy.HelperPreservationPolicy(changed, arm='preserve_declared_helpers')
            after = controller.consume_model(text, finish_reason='stop')
            if before['done'] or after['done']:
                row['reason'] = 'no_nonterminal_public_review'
            else:
                row.update(eligible=True, before=review(original), after=review(changed),
                    transformed=bool(after['controller_actions']))
            rows.append(row)
    good = [r for r in rows if r['eligible']]
    field = lambda r, which: r[which]['passed'] if type(r[which]['passed']) is int else None
    comparable = [r for r in good if field(r, 'before') is not None and field(r, 'after') is not None]
    full = lambda r, key: type(r[key]['total']) is int and r[key]['total'] > 0 and r[key]['passed'] == r[key]['total']
    return dict(kind='posthoc_public_source_helper_preservation', original_assigned=8,
        original_first_replies=len(rows), eligible_complete_proposals=len(good),
        transformed_proposals=sum(r['transformed'] for r in good),
        comparable_public_field_reviews=len(comparable),
        public_field_review_unavailable=len(rows)-len(comparable),
        review_kind_pairs=dict(Counter(str(r['before']['kind'])+' -> '+str(r['after']['kind']) for r in good)),
        original_all_public_pass=sum(full(r, 'before') for r in comparable),
        preserved_all_public_pass=sum(full(r, 'after') for r in comparable),
        public_field_improved=sum(field(r, 'after') > field(r, 'before') for r in comparable),
        public_field_regressed=sum(field(r, 'after') < field(r, 'before') for r in comparable),
        skip_reasons=dict(Counter(r['reason'] for r in rows if not r['eligible'])),
        original_source=a.expected_source, original_assessment_sha256=a.assessment_sha256,
        policy_sha256=sha(Path(__file__).with_name('helper_policy.py')),
        analysis_sha256=sha(__file__), row_digest=protocol.digest(rows),
        hidden_final_grades_consulted=False, controller_authored_counterfactual=True,
        new_model_calls=0, new_procedural_cases=0, candidate_measured=False,
        model_improvement=False, leaderboard_gain=False)


if __name__ == '__main__':
    p = argparse.ArgumentParser(allow_abbrev=False)
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--expected-source', required=True)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--assessment-sha256', required=True)
    p.add_argument('--screen-gate', type=Path, required=True)
    p.add_argument('--screen-gate-sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    result = run(a)
    with a.output.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps(result))
