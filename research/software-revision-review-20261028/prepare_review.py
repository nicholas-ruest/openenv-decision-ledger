"""Stage the qualified revision candidate for human review. No network or provider calls."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / p) for p in (
    'research/software-revision-candidate-20261028',
    'research/software-public-check-20261028', 'integrations/software-repair')]
from revision_environment import RevisionEnvironment, RevisionAction, RevisionObservation, TASKS
from revision_app import app
from fastapi.testclient import TestClient

SOURCE = 'ae301b0a4071b5a376d6eeef6812060fac789534'
IMAGE = 'ghcr.io/nicholas-ruest/openenv-decision-ledger@sha256:a842e4ec292f9aa5067514a7eb8a85b5fa1e43edda61ef2bb53b9704603f8144'
SCHEMA_SHA = 'b2828883f206a3976c8ed82f53380f5984a30e16ab88ed06d116233a6bee9814'
# Exported public examples are NOT future confirmation cases. No old archive is reused.
SPLITS = {'train': (2360000, 16), 'validation': (2361000, 4), 'test': (2362000, 4)}

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + '\n').encode()

def request():
    # In-process native HTTP route, with exact full-schema digest previously checked in image CI.
    schema = TestClient(app).get('/schema').json()
    if sha(canonical(schema).encode()) != SCHEMA_SHA:
        raise ValueError('qualified image schema drift')
    limits = dict(split='train', reset_wall_s=120, rollout_wall_s=600,
                  verifier_wall_s=30, tool_wall_s=20, tool_calls_total=2,
                  tool_calls_per_minute=60, completion_tokens=8192,
                  context_tokens=24576, cpu_floor_vcpus=1, memory_gib=2, workspace_gib=2)
    return dict(submission_id='decision-ledger-software-feedback-v14-20261028',
                name='Decision Ledger: software repair with public-example revision',
                image=IMAGE, source='https://github.com/nicholas-ruest/openenv-decision-ledger/tree/' + SOURCE,
                dataset='GlobalBusinessAdvisors/openenv-decision-ledger',
                schema={k: schema[k] for k in ('action', 'observation')},
                tasks=[dict(task_id=t, **limits) for t in TASKS],
                example_actions=[dict(content='', submit=False), dict(content='', submit=True)],
                finish_action=dict(content='', submit=True))

def source_files(root):
    # Explicit allowlist; never archive workspaces, provider data, credentials or caches.
    files = list((root / 'integrations/software-repair/repair_env').glob('*.py'))
    files += [root / p for p in (
        'LICENSE', 'THIRD_PARTY.md', 'integrations/software-repair/Dockerfile.direct',
        'integrations/openenv-arena/requirements.lock',
        'research/software-revision-image-20261028/Dockerfile',
        'research/software-revision-candidate-20261028/revision_environment.py',
        'research/software-revision-candidate-20261028/revision_app.py',
        'research/software-public-check-20261028/public_check.py')]
    return sorted(files)

def build(output, root=ROOT):
    output.mkdir(exist_ok=False)
    req = request()
    # Bind source bytes to the already-qualified frozen source, including unchanged repair_env.
    import subprocess
    hashes = {}
    with zipfile.ZipFile(output / 'environment-source.zip', 'x') as archive:
        for path in source_files(root):
            if path.is_symlink() or not path.is_file():
                raise ValueError('regular allowlisted source required')
            name = path.relative_to(root).as_posix()
            data = path.read_bytes()
            frozen = subprocess.check_output(['git', '-C', str(root), 'show', SOURCE + ':' + name])
            if data != frozen:
                raise ValueError('source differs from qualified image: ' + name)
            hashes[name] = sha(data)
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            archive.writestr(entry, data)
    observations = set()
    identities = set()
    counts = {}
    for split, (start, count) in SPLITS.items():
        rows = []
        for task in TASKS:
            for seed in range(start, start + count):
                env = RevisionEnvironment()
                obs = env.reset(task_id=task, seed=seed).model_dump()
                # No internal task, reference source, hidden inputs, or hidden labels exported.
                value = canonical(obs)
                if (task, seed) in identities or sha(value.encode()) in observations:
                    raise ValueError('duplicate captured reset')
                identities.add((task, seed)); observations.add(sha(value.encode()))
                rows.append(dict(task_id=task, seed=seed, split=split,
                                 kind='captured_native_reset_observation', observation=obs,
                                 observation_sha256=sha(value.encode())))
        (output / (split + '.jsonl')).write_text(''.join(canonical(r) + '\n' for r in rows))
        counts[split] = len(rows)
    # Admission actions actually terminate both tasks. These are negative controls, not solves.
    controls = []
    for task in TASKS:
        env = RevisionEnvironment(); env.reset(task_id=task, seed=2363000)
        first, final = [env.step(RevisionAction(**a)) for a in req['example_actions']]
        if first.done or first.reward != 0 or not final.done or final.reward != 0:
            raise ValueError('admission example sequence failed')
        controls.append(dict(task_id=task, seed=2363000, first_done=first.done,
                             final_done=final.done, final_reward=final.reward))
    (output / 'submission-candidate.json').write_bytes(encoded(req))
    (output / 'README.md').write_text(CARD)
    manifest = {p.name: sha(p.read_bytes()) for p in sorted(output.iterdir())}
    review = dict(approved=False, submitted=False, dataset_uploaded=False, new_model_calls=0,
                  runtime_source=SOURCE, image=IMAGE, schema_sha256=SCHEMA_SHA,
                  request_sha256=manifest['submission-candidate.json'],
                  source_file_sha256=hashes, manifest=manifest, split_counts=counts,
                  captured_public_resets=len(identities), unique_reset_observations=len(observations),
                  source_archive_allowlisted=True, example_negative_controls=controls,
                  fresh_model_confirmation=False, leaderboard_improvement=False,
                  qualification_ci=40742200919,
                  approval_scope='Exact request and matching dataset replacement both require interactive approval.',
                  dataset_status='Staged only; current HF revision still describes v11. Must not submit this request against that stale dataset.',
                  matched_protocol='Separate research/software-public-check-20261028/revision-plan.json uses 4096/8192 tokens, whereas this request retains v12 8192/24576; not equivalent.')
    (output / 'REVIEW.json').write_bytes(encoded(review))
    return review

CARD = '''---
license: mit
task_categories:
- reinforcement-learning
---

# Software repair with public-example revision — unapproved v14 candidate

Two equal-weight prerequisite tasks: implement ignore-rule aggregation with matching
supplied (d3), or matching with aggregation supplied (d4). This changes the mix from
v12, which also included joint d2. No causal mix benefit has been established.

The initial observation supplies source, a language contract and six examples.
A first proposed complete module receives bounded feedback from only those examples.
The second response is final; submit=true may finish early. Intermediate reward is
zero. The unchanged independent hidden-case grader determines final reward;
unchanged/non-improving code earns zero and valid partial repairs can earn partial
reward. Candidate code runs in the existing bounded interpreter, without host exec.

The image digest and exact request are in submission-candidate.json; the source
allowlist and file hashes are in REVIEW.json. environment-source.zip reproduces the
qualified source overlay over its digest-pinned base. Forty-eight public reset
observations (32 train, 8 validation, 8 test) use disjoint split seeds. They illustrate
the runtime rather than constrain Arena seed sampling. Public exported test examples
are not unseen confirmation, and no hidden answer sets are exported.

The two scripted admission episodes are negative controls, not model solves. Prior
posthoc replay found four partial repairs failed visible examples, but no fresh model
comparison has established that this feedback improves final repairs or training.
Model improvement, private transfer and leaderboard gain remain unmeasured.
The matched research protocol has smaller token limits than this Arena request.

This bundle is staged only. It does not grant permission to replace the existing HF
dataset or submit to Arena; both require Nick's interactive exact-request approval.
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.output), sort_keys=True))
