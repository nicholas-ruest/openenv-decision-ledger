"""Explicit empty-action finalization for a separate deployment candidate."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/p) for p in (
    'research/software-public-review-default-20261030',
    'research/software-public-check-20261028',
    'integrations/software-repair')]
from review_environment import PublicReviewEnvironment
from mandatory_environment import ProposalAction
from joint_revision_environment import RevisionEnvironment,RevisionAction

class PortableReviewEnvironment(PublicReviewEnvironment):
    _finish_action=ProposalAction()
    def reset(self,*args,**kwargs):
        obs=super().reset(*args,**kwargs)
        old=('You have two responses. Your first response is a proposal only and always receives a review turn. '
            'Your second response is final. The action contains only content; there is no early-submit command. '
            'On the second response, empty content retains your proposal.')
        new=('You have at most two responses. A nonempty first module receives a review turn at reward zero. '
            'The second response is final. Empty content ends the episode at any point and grades the current module. '
            'The action contains only content.')
        if old not in obs.prompt:
            raise ValueError('frozen research prompt changed')
        return obs.model_copy(update={'prompt':obs.prompt.replace(old,new)})
    def step(self,action:ProposalAction,timeout_s=None,**kwargs):
        if not action.content:
            return RevisionEnvironment.step(self,RevisionAction(content='',submit=True),
                timeout_s=timeout_s,**kwargs)
        return super().step(action,timeout_s=timeout_s,**kwargs)
