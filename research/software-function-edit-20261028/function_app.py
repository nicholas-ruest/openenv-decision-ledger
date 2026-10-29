"""Separate experimental native app; frozen reviewed servers are unaffected."""
from openenv.core.env_server.http_server import create_app
from function_edit import FunctionEditEnvironment, FunctionEditAction
from repair_env.direct_environment import DirectRepairObservation

app = create_app(
    FunctionEditEnvironment, FunctionEditAction, DirectRepairObservation,
    env_name="decision_ledger_function_repair", max_concurrent_envs=8,
)
