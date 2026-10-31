"""Research app for Native transport qualification, with no paid caller."""
from contract_environment import ContractEnvironment
from mandatory_environment import ProposalAction
from joint_revision_environment import RevisionObservation
from openenv.core.env_server.http_server import create_app


class ContractServerEnvironment(ContractEnvironment):
    def __init__(self):
        super().__init__(arm='explicit_contract')


app = create_app(ContractServerEnvironment, ProposalAction, RevisionObservation,
                 env_name='decision_ledger_output_contract', max_concurrent_envs=8)
