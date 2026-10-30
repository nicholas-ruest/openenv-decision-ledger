"""Separate candidate app; no production image is changed."""
from diagnostic_environment import DiagnosticEnvironment
from mandatory_environment import ProposalAction
from joint_revision_environment import RevisionObservation
from openenv.core.env_server.http_server import create_app
class SourceDiagnosticServerEnvironment(DiagnosticEnvironment):
    def __init__(self):
        super().__init__(arm='diagnostic_review')
app=create_app(SourceDiagnosticServerEnvironment,ProposalAction,RevisionObservation,
    env_name='decision_ledger_source_diagnostic',max_concurrent_envs=8)
