"""Separate experimental app; does not retarget either reviewed server."""
from openenv.core.env_server.http_server import create_app
from runtime_environment import DomainCueEnvironment
from repair_env.direct_environment import DirectRepairAction
from runtime_environment import qualified
app=create_app(DomainCueEnvironment,DirectRepairAction,qualified.original.Observation,
               env_name='decision_ledger_final_domain_candidate',max_concurrent_envs=8)
