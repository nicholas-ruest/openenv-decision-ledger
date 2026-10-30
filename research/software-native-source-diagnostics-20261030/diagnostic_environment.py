"""Source-only parser feedback in a separate controlled deployment candidate."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT/'research/software-retain-public-passing-20261030'))
from portable_environment import PortableReviewEnvironment
from source_diagnostics import diagnose

class DiagnosticEnvironment(PortableReviewEnvironment):
    def __init__(self,*,arm):
        if arm not in ('standard_review','diagnostic_review'):
            raise ValueError('explicit parser-diagnostic arm required')
        self.diagnostic_arm=arm
        super().__init__(arm='public_review')
    def step(self,action,timeout_s=None,**kwargs):
        obs=super().step(action,timeout_s=timeout_s,**kwargs)
        if obs.done or self.diagnostic_arm!='diagnostic_review':
            return obs
        review=json.loads(obs.feedback)
        if review.get('kind')!='candidate_rejected':
            return obs
        diagnostic=diagnose(action.content)
        if diagnostic is not None:
            review['source_diagnostic']=diagnostic
        return obs.model_copy(update={'feedback':json.dumps(review,sort_keys=True,separators=(',',':'))})
