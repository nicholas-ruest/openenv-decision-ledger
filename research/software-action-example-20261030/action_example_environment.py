"""An action-instance example as a separate, unmeasured prompt intervention."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / p) for p in (
    'research/software-output-contract-20261030',
    'research/software-terminal-audit-20261028',
    'research/software-revision-candidate-20261028',
    'research/software-public-check-20261028',
    'integrations/software-repair',
)]
from contract_environment import ContractEnvironment
from mandatory_environment import ProposalAction

ACTION_EXAMPLE_NOTE = (
    '\nAction serialization example: {"content":"<complete repaired Python module>"}. '
    'Replace the placeholder with your actual Python source, encoded as a JSON string. '
    'Return an action object with field values; do not return the JSON Schema '
    'description of the action. The example is only an output-shape guide, not a solution.'
)


class ActionExampleEnvironment(ContractEnvironment):
    """Both arms use the unchanged baseline environment and parser.

    No output-contract emphasis is included in either arm. The treatment adds
    only a fixed JSON-instance example to the reset prompt. Schema echoes still
    follow existing empty-content behavior; this does not silently fix parsing.
    """
    def __init__(self, *, arm):
        if arm not in ('schema_only', 'action_example'):
            raise ValueError('explicit action-example arm required')
        self.action_example_arm = arm
        super().__init__(arm='standard_contract')

    def reset(self, *args, **kwargs):
        obs = super().reset(*args, **kwargs)
        if self.action_example_arm == 'action_example':
            return obs.model_copy(update={'prompt': obs.prompt + ACTION_EXAMPLE_NOTE})
        return obs
