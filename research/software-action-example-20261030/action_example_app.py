"""Separate source-only SDK app; no production runtime/image replacement."""
from action_example_environment import ActionExampleEnvironment, ProposalAction
from joint_revision_environment import RevisionObservation
from openenv.core.env_server.http_server import create_app


class SourceActionExampleServerEnvironment(ActionExampleEnvironment):
    def __init__(self):
        super().__init__(arm='action_example')


app = create_app(SourceActionExampleServerEnvironment, ProposalAction, RevisionObservation,
                 env_name='decision_ledger_action_example', max_concurrent_envs=8)
