"""Posthoc first-proposal retention audit. No provider or admission entry point.

The trigger uses public review fields only. Empty-action finalization is a
controller-authored counterfactual, never an observed model response or solve.
Run each protocol in a separate process to avoid historical module-name clashes.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
PROTOCOLS = {
    'output_contract': 'software-output-contract-20261030',
    'action_example': 'software-action-example-20261030',
}
TOKENIZER_SHA = '0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def public_pass(review):
    return (type(review) is dict and review.get('kind') == 'public_field_check'
        and review.get('public_only') is True and review.get('hidden_access') is False
        and type(review.get('passed')) is int and type(review.get('total')) is int
        and review['total'] > 0 and review['passed'] == review['total'])


def counterfactual(trial, response):
    """Do not consult a hidden grade to decide whether to retain a proposal."""
    choice = response['choices'][0]
    if choice.get('finish_reason') != 'stop':
        return dict(eligible=False, reason='first_response_not_complete')
    first = trial.consume(choice['message'].get('content'))
    if first['done'] or not trial.native:
        return dict(eligible=False, reason='no_nonterminal_public_review')
    observation = trial.native[-1]
    if observation['done'] or observation['reward'] != 0 or observation['stage'] != 'revision':
        raise ValueError('original zero-reward public review required')
    review = json.loads(observation['feedback'])
    if not public_pass(review):
        return dict(eligible=False, reason='public_examples_not_all_passing',
                    public_passed=review.get('passed'), public_total=review.get('total'))
    # The public-only decision is complete before this Native hidden evaluation.
    final = trial.consume(json.dumps(dict(content='')))
    if not final['done'] or final['category'] not in ('full', 'partial', 'wrong'):
        raise ValueError('unchanged proposal must receive an ordinary Native grade')
    return dict(eligible=True, public_passed=review['passed'], public_total=review['total'],
                retained_category=final['category'], retained_reward=final['semantic_reward'],
                controller_authored_action=True)


def run(args):
    root = args.source_root.resolve()
    if subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip() != args.expected_source:
        raise ValueError('exact original source required')
    subprocess.run(['git', '-C', str(root), 'diff', '--quiet', 'HEAD'], check=True)
    if subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain'], text=True).strip():
        raise ValueError('clean original source required')
    protocol_dir = root / 'research' / PROTOCOLS[args.protocol]
    sys.path.insert(0, str(protocol_dir))
    import caller
    protocol, Trial = caller.modules()
    from replay import verify_chunk
    helper = caller.load('first_proposal_counter', root / 'integrations/openenv-arena/scripts/calibrate.py')
    counter = helper.load_counter(argparse.Namespace(accounting='arena', tokenizer_json=args.tokenizer,
                                                   tokenizer_sha256=TOKENIZER_SHA))
    rows = []; identities = []; call_ids = []; archives = []
    for index in range(args.completed_chunks):
        parent = args.archive / f'chunk{index}'
        frozen = json.loads((parent / 'inputs.json').read_text())
        complete = json.loads((parent / 'live/complete.json').read_text())
        if (frozen != protocol.bundle(index) or complete.get('scripted') is not False
                or complete['source_inputs_sha256'] != protocol.digest(frozen)):
            raise ValueError('original live archive required')
        observed = [json.loads(x) for x in (parent / 'live/records.jsonl').read_text().splitlines()]
        events = [json.loads(x) for x in (parent / 'live/events.jsonl').read_text().splitlines()]
        if any(x['generation_tokens'] is None or x['category'] in ('provider', 'budget') for x in observed):
            raise ValueError('fully known original responses required')
        proof = verify_chunk(frozen, observed, events, counter)
        identities += proof['response_ids']; call_ids += proof['call_ids']
        archives.append(dict(chunk=index, records_sha256=digest(observed), events_sha256=digest(events)))
        for job, actual in zip(frozen['screen_jobs'], observed):
            first = next(e for e in events if e['event'] == 'response'
                         and e['attempt_id'] == job['attempt_id'] and e['turn'] == 0)
            retained = counterfactual(Trial(job), first['response'])
            rows.append(dict(arm=job['arm'], sample=job['sample'], actual_category=actual['category'],
                             actual_reward=actual['semantic_reward'], **retained))
    if len(set(identities)) != len(identities) or len(set(call_ids)) != len(call_ids):
        raise ValueError('reused replies or calls')
    groups = {}
    for arm in protocol.ARMS:
        arm_rows = [r for r in rows if r['arm'] == arm]
        eligible = [r for r in arm_rows if r['eligible']]
        groups[arm] = dict(recorded=len(arm_rows), eligible=len(eligible),
            actual_categories=dict(Counter(r['actual_category'] for r in arm_rows)),
            eligible_actual_categories=dict(Counter(r['actual_category'] for r in eligible)),
            retained_categories=dict(Counter(r['retained_category'] for r in eligible)),
            truncations_with_full_first_proposal=sum(r['actual_category'] == 'truncation'
                and r['retained_category'] == 'full' for r in eligible))
    return dict(analysis='posthoc_public_triggered_first_proposal_retention', protocol=args.protocol,
        source=args.expected_source, original_assigned=8, original_recorded=len(rows),
        original_calls=len(call_ids), original_known_replies=len(identities), groups=groups,
        row_digest=digest(rows), archive_digests=archives, trigger_uses_hidden_grade=False,
        controller_authored_counterfactual=True, new_model_calls=0, fresh_cases=0,
        candidate_measured=False, model_improvement=False, leaderboard_gain=False, is_training=False)


def main():
    p = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--expected-source', required=True)
    p.add_argument('--protocol', choices=PROTOCOLS, required=True)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--completed-chunks', type=int, choices=(1, 2, 3, 4), required=True)
    p.add_argument('--tokenizer', type=Path, required=True)
    print(json.dumps(run(p.parse_args()), sort_keys=True))


if __name__ == '__main__':
    main()
