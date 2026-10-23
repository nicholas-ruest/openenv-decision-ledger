from openenv.core.env_server.http_server import create_app

from .direct_environment import DirectRepairAction, DirectRepairEnvironment, DirectRepairObservation

app = create_app(DirectRepairEnvironment, DirectRepairAction, DirectRepairObservation,
                 env_name="decision_ledger_direct_repair", max_concurrent_envs=8)
