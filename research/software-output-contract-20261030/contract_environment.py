"""Fixed, public contract emphasis; no grader, fixture or budget changes."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / 'research/software-public-runtime-diagnostics-20261030'))
from diagnostic_environment import DiagnosticEnvironment
from joint_revision_environment import RevisionObservation

CONTRACT_NOTE = (
    '\nOutput-contract check: the returned dictionary must have exactly the paths '
    'from the supplied entries as its keys, with one boolean value per entry. '
    'Use implicit parent paths internally to determine status; do not add them '
    'to the returned dictionary unless they are themselves supplied entries. '
    'Do not add normalized aliases, rule strings, or diagnostic fields to that result.'
)


class ContractEnvironment(DiagnosticEnvironment):
    def __init__(self, *, arm):
        if arm not in ('standard_contract', 'explicit_contract'):
            raise ValueError('explicit output-contract arm required')
        self.contract_arm = arm
        super().__init__(arm='diagnostic_review')

    def reset(self, seed=None, episode_id=None, **kwargs):
        # The inherited calibration wrapper only admits ignore-d3. This separate
        # wrapper resets the actual Native ignore-d2 task; it never relabels d3.
        task = kwargs.get('task_id', 'software_repair-ignore-d2')
        if task != 'software_repair-ignore-d2':
            raise ValueError('explicit joint ignore-d2 task required')
        native = self._direct.reset(seed=seed, episode_id=episode_id, task_id=task)
        self._terminal = None
        self._steps = 0
        self._visible = {'examples': native.examples}
        self._write_error = ''
        marker = '\nRepair the supplied source. Reply once'
        if marker not in native.prompt:
            raise ValueError('frozen Native instruction contract changed')
        prompt = native.prompt.split(marker)[0] + (
            '\nPropose a complete repaired Python module as one JSON action. '
            'You have at most two responses. A nonempty first module receives a review turn at reward zero. '
            'The second response is final. Empty content ends the episode at any point and grades the current module. '
            'The action contains only content. '
            'Intermediate observations award no reward. Final reward uses the unchanged complete contract and independent hidden cases.'
        )
        obs = RevisionObservation(task_id=task, prompt=prompt, source=native.source,
                                  examples=native.examples, stage='proposal',
                                  remaining_responses=2, reward=0, done=False)
        if self.contract_arm == 'explicit_contract':
            return obs.model_copy(update={'prompt': obs.prompt + CONTRACT_NOTE})
        return obs
