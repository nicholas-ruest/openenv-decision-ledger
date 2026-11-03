"""Independent literal fixture for Profa-QE's MIT-licensed media-d2 subtitles.

Uses the public solver as trusted reference code. No task generator, model,
terminal/server session, provider, financial API or MetaHarness is invoked.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

PINS = {
    'qe_arena/skills/media.py': '005eabea342ba948e6b68dcc341f3756a8ebdd5fb44830cb13bb482a16ef200c',
    'qe_arena/skills/subtitles.py': '872054f7309500113beab2c853bfeceebd146e60dc36d42f42f9e98e6c4a7b84',
    'LICENSE': 'e0a8e97900a1184396b65bca8507d5c7b1a6df58537b61722dfe0f416990f0e2',
}

# Hand-authored, intentionally reversed. This is not a sampled Arena task.
INPUT = '9\n00:00:11,020 --> 00:00:12,000\nBeta.\n\n4\n00:00:10,000 --> 00:00:11,000\nAlpha.\n'
# Exact ratio is 23.976/25 = 2997/3125. Independently calculated rounded
# rescaled+shifted times: A=(10090,11049), B=(11069,12008). The 80ms gap
# clips only A's end to 10989. Literal expected output does not call helpers.
EXPECTED = '1\n00:00:10,090 --> 00:00:10,989\nAlpha.\n\n2\n00:00:11,069 --> 00:00:12,008\nBeta.\n'
EXPECTED_CUES = [(1, 10090, 10989, ['Alpha.']), (2, 11069, 12008, ['Beta.'])]


def check(root):
    root = Path(root).resolve()
    for relative, expected in PINS.items():
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected:
            raise ValueError('public source lease differs: ' + relative)
    sys.path.insert(0, str(root))
    from qe_arena import skills
    from qe_arena.skills import subtitles
    if Path(subtitles.__file__).resolve() != root / 'qe_arena/skills/subtitles.py':
        raise ValueError('unexpected imported reference module')
    assert 'subtitles' not in skills.SERVED['qe_skill-media-d1']
    assert 'subtitles' in skills.SERVED['qe_skill-media-d2']
    files = {'input.srt': INPUT, 'job.json': json.dumps({
        'source_fps': '23.976', 'target_fps': '25', 'shift_ms': 500,
        'min_gap_ms': 80,
    })}
    correct = subtitles._solve(files, 2, None)
    assert correct == EXPECTED, 'literal pipeline result differs'
    assert all(subtitles._check(EXPECTED_CUES, correct))
    rejected = {}
    for variant in ('wrong_sign', 'no_sort', 'no_rate', 'inverted_rate', 'shift_first', 'no_gap'):
        text = subtitles._solve(files, 2, variant)
        rejected[variant] = not all(subtitles._check(EXPECTED_CUES, text))
        assert rejected[variant], 'fixture failed to distinguish ' + variant
    return {
        'kind': 'hand_authored_subtitle_pipeline_control',
        'source_pins': PINS, 'literal_output_matches': True,
        'wrong_methods_rejected': rejected, 'task_generator_called': False,
        'media_d1_has_subtitles': False, 'media_d2_has_subtitles': True,
        'new_model_calls': 0, 'generated_task_cases': 0,
        'model_improvement': False, 'is_training': False,
        'actual_metaharness_executed': False,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--upstream', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(check(args.upstream), indent=2))
