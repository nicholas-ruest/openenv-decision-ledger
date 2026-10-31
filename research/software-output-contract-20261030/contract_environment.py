"""Fixed, public contract emphasis; no grader, fixture or budget changes."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / 'research/software-public-runtime-diagnostics-20261030'))
from diagnostic_environment import DiagnosticEnvironment

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

    def reset(self, *args, **kwargs):
        obs = super().reset(*args, **kwargs)
        if self.contract_arm == 'explicit_contract':
            return obs.model_copy(update={'prompt': obs.prompt + CONTRACT_NOTE})
        return obs
