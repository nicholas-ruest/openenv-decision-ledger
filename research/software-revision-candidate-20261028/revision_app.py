"""Separate experimental app. Does not retarget the frozen software server."""
from openenv.core.env_server.http_server import create_app
from revision_environment import RevisionEnvironment,RevisionAction,RevisionObservation
app=create_app(RevisionEnvironment,RevisionAction,RevisionObservation,
               env_name='decision_ledger_revision_repair',max_concurrent_envs=8)
