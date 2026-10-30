"""Computed-public feedback vs neutral review, without sampler controls."""
import json
from mandatory_environment import RequiredReviewEnvironment

class PublicReviewEnvironment(RequiredReviewEnvironment):
    def __init__(self,*,arm):
        if arm not in ('neutral_review','public_review'):
            raise ValueError('explicit separate review arm required')
        self.review_arm=arm
        super().__init__(arm='field_contract')

    def step(self,action,**kwargs):
        obs=super().step(action,**kwargs)
        if obs.done:
            return obs
        review=json.loads(obs.feedback)
        advice='Review the proposed module against the original contract and supplied examples. Return the complete final module; no further review follows.'
        if self.review_arm=='neutral_review':
            review=dict(kind='neutral_review',public_only=True,hidden_access=False,
                contract_reminder=review['contract_reminder'])
        review['review_advice']=advice
        return obs.model_copy(update={'feedback':json.dumps(review,sort_keys=True,separators=(',',':'))})
