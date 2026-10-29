"""Build an offline, unapproved request from the measured immutable media image."""
import argparse
import hashlib
import json
from pathlib import Path

IMAGE = 'ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:b80078c2cc8a05d3222fe22ee91321d29d881afff912097c6601a8cffd84c4e6'
SOURCE = '74a8727fa14270e29cf363fc2ad79b0f7f9cbce1'
UPSTREAM = '958198e55299eb18ad812f438a6b2ca6abaa7f5c'
TASKS = ('qe_skill-media-d1', 'qe_skill-media-d2')


def request(evidence, upstream_request):
    assert (evidence/'image.txt').read_text().strip() == IMAGE, 'image mismatch'
    assert (evidence/'source.txt').read_text().strip() == SOURCE, 'source mismatch'
    schema = json.loads((evidence/'schema.json').read_text())
    assert set(schema) >= {'action','observation'}, 'schema incomplete'
    # Exact source schemas, not a hand-written approximation.
    assert schema['action'] == upstream_request['schema']['action'], 'action schema drift'
    assert schema['observation'] == upstream_request['schema']['observation'], 'observation schema drift'
    checks = json.loads((evidence/'anonymous-tcp.json').read_text())
    assert all(checks.get(k) is True for k in ('health','schema','uid_shell'))
    assert checks.get('pid1') == 'tini' and checks.get('tcp_reference_episodes') == 2
    selected = [t for t in upstream_request['tasks'] if t['task_id'] in TASKS]
    assert tuple(t['task_id'] for t in selected) == TASKS
    assert all(t['split']=='train' and t['completion_tokens']==4096 and t['context_tokens']==8192 and t['tool_calls_total']==32 for t in selected)
    return {
        'submission_id':'decision-ledger-media-v13-20261027',
        'name':'Decision Ledger media terminal: attributed Profa-QE adaptation',
        'image':IMAGE, 'server_port':8000, 'schema':{k:schema[k] for k in ('action','observation')},
        'tasks':selected, 'example_actions':[{'action_type':'evaluate'}],
        'finish_action':{'action_type':'evaluate'},
        'dataset':'GlobalBusinessAdvisors/openenv-decision-ledger',
        'source':f'https://github.com/nicholas-ruest/openenv-decision-ledger/tree/{SOURCE}',
    }


def prepare(evidence, upstream_request, output):
    if output.exists():
        raise ValueError('fresh output required')
    req = request(evidence, upstream_request)
    output.mkdir(parents=True)
    data = (json.dumps(req,indent=2,sort_keys=True)+'\n').encode()
    (output/'request.json').write_bytes(data)
    manifest = {
        'request_sha256':hashlib.sha256(data).hexdigest(),
        'image':IMAGE, 'runtime_source':SOURCE, 'upstream_source':UPSTREAM,
        'approved':False, 'submitted':False, 'dataset_replaced':False,
        'hypothesis':'Media-only specialization; removes five science/math cells from the public mixed v7 recipe. Causal benefit unconfirmed.',
        'evidence_files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(evidence.iterdir()) if p.is_file()},
        'prior_runtime_ci':40592567666,
        'software_v12_changed':False,
        'remaining':['Fresh-runner qualification must pass and exact image/schema remain matched.','Dataset source/attribution packet must be reviewed before replacement.','Nick must explicitly approve this exact request before HF replacement or Arena POST.'],
    }
    (output/'REVIEW.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    return manifest


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--upstream-request',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(prepare(a.evidence,json.loads(a.upstream_request.read_text()),a.output),indent=2))
