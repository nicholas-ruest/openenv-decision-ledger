"""Reproduce public subtitle controls; never calls a model or executes a shell."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def audit(source):
    expected = {'qe_arena/skills/__init__.py': '5e0050e8e65569c14cf70963755254f75456f6597177a25e014373ae37cdb3c9', 'qe_arena/skills/media.py': '005eabea342ba948e6b68dcc341f3756a8ebdd5fb44830cb13bb482a16ef200c', 'qe_arena/skills/subtitles.py': '872054f7309500113beab2c853bfeceebd146e60dc36d42f42f9e98e6c4a7b84'}
    for name, sha in expected.items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != sha:
            raise ValueError('pinned public source changed')
    sys.path.insert(0, str(source))
    from qe_arena import skills
    records = []
    for seed in range(2220000, 2220016):
        task = skills.make_skill_task('qe_skill-media-d2', seed, pool=('subtitles',))
        reference = skills.grade(task, skills.solve(task))
        wrong = {name: skills.grade(task, skills.solve(task, name))
                 for name, levels in task.private['family'].traps.items() if 2 in levels}
        if reference != 1 or any(wrong.values()) or skills.grade(task, '') != 0:
            raise ValueError('upstream subtitle oracle or trap control failed')
        records.append({'seed': seed, 'reference_reward': reference,
                        'wrong_method_rewards': wrong,
                        'visible_files_bytes': sum(len(v.encode()) for v in task.files.values()),
                        'case_sha256': hashlib.sha256(json.dumps(task.files, sort_keys=True).encode()).hexdigest()})
    if len({r['case_sha256'] for r in records}) != len(records):
        raise ValueError('duplicate fixture')
    return {'source_repository': 'proffesor-for-testing/openenv-qe-arena',
            'source_commit': '958198e55299eb18ad812f438a6b2ca6abaa7f5c',
            'license': 'MIT; copyright2026 Dragan Spiridonov', 'fixtures': records,
            'model_calls': 0, 'is_training': False, 'model_improvement_claim': False,
            'limitations': ['binary grader; no partial reward', 'not terminal/container validation']}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    with a.output.open('x') as out:
        json.dump(audit(a.source), out, indent=2)
