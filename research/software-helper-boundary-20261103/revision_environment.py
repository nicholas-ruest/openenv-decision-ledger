"""Offline helper-input reminder candidate; no live case or caller admission."""
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'research/software-entry-order-review-20261101'
sys.path.insert(0, str(BASE))
spec = importlib.util.spec_from_file_location('helper_boundary_common_review', BASE / 'revision_environment.py')
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)
ARMS = ('common_review', 'helper_input_boundary')
REMINDER = (
    "When calling a supplied helper, pass arguments in the representation its contract expects. "
    "If you preprocess an argument, preserve all contract-relevant information at the call boundary. "
    "In particular, do not pass a stripped rule pattern to a helper that expects original rule syntax; "
    "retain its negation, anchoring and directory markers in the value passed to that helper."
)


class RevisionEnvironment(original.RevisionEnvironment):
    def __init__(self, *, arm):
        if arm not in ARMS:
            raise ValueError('explicit offline qualification arm required')
        self.boundary_arm = arm
        super().__init__(arm='relation_only')

    def step(self, action, timeout_s=None):
        value = super().step(action, timeout_s)
        if value.stage == 'revision' and self.boundary_arm == 'helper_input_boundary':
            feedback = json.loads(value.feedback)
            feedback['helper_input_boundary_reminder'] = REMINDER
            return value.model_copy(update={'feedback': original.canonical(feedback)})
        return value


def materialize(*args, **kwargs):
    raise ValueError('screen, confirmation, case lease and live caller are unsealed')


def plan():
    return dict(kind='helper_input_boundary_offline_candidate', arms=list(ARMS),
        baseline='Existing common relation review; computed diagnostic withheld',
        treatment='Same review plus helper argument representation reminder',
        qualification_seed=original.QUALIFICATION_SEED, limits=original.plan()['limits'],
        first_prompts_identical=True, samples_per_arm=4, assignments_per_phase=8,
        max_requests_per_phase=16, screen_case_selected=False, confirmation_case_selected=False,
        no_controller_code_edits=True, final_native_grader_unchanged=True,
        comparison_protocol_qualified=False, live_execution_ready=False,
        new_model_calls=0, new_unique_cases=0, model_improvement=False, is_training=False)
