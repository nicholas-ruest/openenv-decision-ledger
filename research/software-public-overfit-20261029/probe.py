"""Negative control: supplied-example memorization is not a full-contract solve.

No model/provider calls. This deliberately wrong candidate is built exclusively
from the reset's visible examples, then independently graded by the native app.
It is a probe, never a training candidate or an automatic repair.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / p) for p in (
    'research/software-revision-candidate-20261028',
    'research/software-public-check-20261028', 'integrations/software-repair')]
from public_check import examples_from_reset
from revision_environment import RevisionEnvironment, RevisionAction, TASKS


def public_only_source(reset):
    rows = examples_from_reset(reset)
    source = ('def classify_ignore(ignore_lines, entries):\n'
              '    for example in ' + repr(rows) + ':\n'
              '        if ignore_lines == example[0][0] and entries == example[0][1]:\n'
              '            return example[1]\n'
              '    return {entry["path"]: False for entry in entries}\n')
    if len(source.encode()) > 8192:
        raise ValueError('unchanged native source limit')
    return source


def run():
    records = []
    # Distinct from all frozen screen/confirmation identities. No private
    # responses, reference implementation, task object or grader passed to
    # the source constructor.
    for task in TASKS:
        env = RevisionEnvironment(arm='public_check')
        reset = env.reset(task_id=task, seed=2470000).model_dump()
        visible = {'examples': reset['examples']}
        source = public_only_source(visible)
        intermediate = env.step(RevisionAction(content=source)).model_dump()
        feedback = json.loads(intermediate['feedback'])
        assert intermediate['reward'] == 0 and not intermediate['done']
        assert feedback['kind'] == 'public_example_check'
        assert feedback['passed'] == feedback['total'] == 6
        assert feedback['execution_errors'] == 0
        # Empty terminal action keeps exactly this deliberately wrong module.
        terminal = env.step(RevisionAction(submit=True)).model_dump()
        assert terminal['done'] and not terminal['error']
        assert terminal['reward'] < 1, 'public fit must not become native full credit'
        records.append(dict(task_id=task, seed=2470000,
                            public_passed=6, public_total=6,
                            native_reward=terminal['reward'],
                            source_bytes=len(source.encode()),
                            source_sha256=hashlib.sha256(source.encode()).hexdigest()))
    return dict(control='deliberately wrong visible-example lookup',
                records=records, model_calls=0, is_training=False,
                fresh_model_confirmation=False, model_improvement=False,
                lesson='Public checks detect some mistakes; passing them cannot replace native full-contract grading.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with args.output.open('x') as stream:
        json.dump(run(), stream, indent=2)
        stream.write('\n')
