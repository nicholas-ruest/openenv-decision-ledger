"""Separate candidate app; no production image is changed."""
from function_revision import FunctionRevisionEnvironment as DiagnosticEnvironment
from function_revision import FunctionRevisionAction as ProposalAction
from joint_revision_environment import RevisionObservation
from openenv.core.env_server.http_server import create_app
class SourceDiagnosticServerEnvironment(DiagnosticEnvironment):
    def __init__(self):
        super().__init__(arm='function_review')
app=create_app(SourceDiagnosticServerEnvironment,ProposalAction,RevisionObservation,
    env_name='decision_ledger_function_revision',max_concurrent_envs=8)
