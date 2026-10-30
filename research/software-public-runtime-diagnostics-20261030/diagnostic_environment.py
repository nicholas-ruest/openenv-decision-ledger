"""Public-only runtime source locations as a separate controlled intervention."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT/'research/software-retain-public-passing-20261030'))
from portable_environment import PortableReviewEnvironment
from public_runtime_diagnostics import diagnose_public


class DiagnosticEnvironment(PortableReviewEnvironment):
    def __init__(self, *, arm):
        if arm not in ('standard_review', 'diagnostic_review'):
            raise ValueError('explicit public runtime diagnostic arm required')
        self.diagnostic_arm = arm
        super().__init__(arm='public_review')

    def step(self, action, timeout_s=None, **kwargs):
        obs = super().step(action, timeout_s=timeout_s, **kwargs)
        if obs.done or self.diagnostic_arm != 'diagnostic_review':
            return obs
        review = json.loads(obs.feedback)
        if review.get('kind') != 'public_field_check':
            return obs
        diagnostic = diagnose_public(action.content, self._direct._core._task)
        if diagnostic is not None:
            review['source_diagnostic'] = diagnostic
        return obs.model_copy(update={'feedback': json.dumps(review, sort_keys=True,
                                                           separators=(',', ':'))})
