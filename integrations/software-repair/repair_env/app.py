from openenv.core.env_server.http_server import create_app

from .environment import RepairAction, RepairEnvironment, RepairObservation

app = create_app(RepairEnvironment, RepairAction, RepairObservation,
                 env_name="decision_ledger_software_repair", max_concurrent_envs=8)
