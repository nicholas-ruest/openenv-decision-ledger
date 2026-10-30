"""Separate candidate HTTP application; no production image is retargeted."""
from openenv.core.env_server.http_server import create_app
from portable_environment import PortableReviewEnvironment,ProposalAction
from joint_revision_environment import RevisionObservation

class PublicReviewServerEnvironment(PortableReviewEnvironment):
    def __init__(self):
        super().__init__(arm='public_review')

app=create_app(PublicReviewServerEnvironment,ProposalAction,RevisionObservation,
    env_name='decision_ledger_public_review',max_concurrent_envs=8)
