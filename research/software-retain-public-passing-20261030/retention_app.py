"""Separate experimental retention-advice app; no existing server is retargeted."""
from openenv.core.env_server.http_server import create_app
from retention_environment import RetentionEnvironment
from mandatory_environment import ProposalAction
from joint_revision_environment import RevisionObservation
class RetentionServerEnvironment(RetentionEnvironment):
    def __init__(self):
        super().__init__(arm='retain_review')
app=create_app(RetentionServerEnvironment,ProposalAction,RevisionObservation,
    env_name='decision_ledger_retention_review',max_concurrent_envs=8)
