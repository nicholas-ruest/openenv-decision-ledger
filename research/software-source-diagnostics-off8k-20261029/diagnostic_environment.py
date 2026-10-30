"""Separate required-review candidate: generic versus explicit source diagnostics."""
import json
from mandatory_environment import RequiredReviewEnvironment
from repair_env.runner import Program
from repair_env.tasks import SOURCE_PATH
from public_check import canonical
from source_diagnostics import augment

ARMS=('generic_feedback','source_diagnostics')

class SourceDiagnosticEnvironment(RequiredReviewEnvironment):
    def __init__(self,*,arm='source_diagnostics'):
        if arm not in ARMS:raise ValueError('exact diagnostic arm required')
        self.diagnostic_arm=arm
        # Both arms receive identical computed public-example checks. The only
        # intervention is explanatory syntax detail on a compiler rejection.
        super().__init__(arm='public_check')
    def step(self,action,timeout_s=None,**kwargs):
        observation=super().step(action,timeout_s=timeout_s,**kwargs)
        if self.diagnostic_arm=='source_diagnostics' and not observation.done:
            public=json.loads(observation.feedback)
            result=augment(public,self._direct._files[SOURCE_PATH],Program)
            return observation.model_copy(update={'feedback':canonical(result)})
        return observation
