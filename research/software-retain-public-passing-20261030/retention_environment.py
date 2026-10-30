"""Preservation advice triggered only by the supplied public examples."""
import json
from portable_environment import PortableReviewEnvironment

class RetentionEnvironment(PortableReviewEnvironment):
    def __init__(self,*,arm):
        if arm not in ('standard_review','retain_review'):
            raise ValueError('explicit retention comparison arm required')
        self.retention_arm=arm
        super().__init__(arm='public_review')

    def step(self,action,timeout_s=None,**kwargs):
        obs=super().step(action,timeout_s=timeout_s,**kwargs)
        if obs.done:
            return obs
        review=json.loads(obs.feedback)
        if (self.retention_arm=='retain_review' and review.get('kind')=='public_field_check'
                and review.get('total',0)>0 and review.get('passed')==review['total']):
            review['retention_advice']=True
            review['review_advice']=(
                'The proposed module passed all supplied public examples. This does not prove the full contract. '
                'Preserve the proposal unless you identify a specific contract violation. '
                'Return {"content":""} to keep it unchanged, or a corrected complete module if needed. '
                'No further review follows.')
        return obs.model_copy(update={'feedback':json.dumps(review,sort_keys=True,separators=(',',':'))})
