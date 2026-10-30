"""A required proposal/review/final sequence in both controlled arms."""
from openenv.core.env_server.types import Action
from pydantic import Field,ConfigDict
from joint_revision_environment import RevisionEnvironment,RevisionAction

class ProposalAction(Action):
    model_config=ConfigDict(extra='ignore')
    content:str=Field(default='',max_length=8192,description='Complete proposed Python module. On the second response, empty content retains the proposal.')

class RequiredReviewEnvironment(RevisionEnvironment):
    """Only the public-versus-neutral feedback differs between arms.

    This is a separate candidate, not a silent modification of reviewed v14.
    The typed action has no early-submit command. Each valid first proposal is
    reviewed at reward zero; only the second response reaches the native grader.
    """
    _finish_action=ProposalAction()
    def reset(self,*args,**kwargs):
        obs=super().reset(*args,**kwargs)
        marker='\nPropose a complete repaired Python module as one JSON action.'
        if marker not in obs.prompt:raise ValueError('frozen revision instruction changed')
        prompt=obs.prompt.split(marker)[0]+('\nPropose a complete repaired Python module as one JSON action. '
            'You have two responses. Your first response is a proposal only and always receives a review turn. '
            'Your second response is final. The action contains only content; there is no early-submit command. '
            'On the second response, empty content retains your proposal. '
            'Intermediate observations award no reward. Final reward uses the unchanged complete contract and independent hidden cases.')
        return obs.model_copy(update={'prompt':prompt})
    def step(self,action:ProposalAction,timeout_s=None,**kwargs):
        return super().step(RevisionAction(content=action.content,submit=False),timeout_s=timeout_s,**kwargs)
