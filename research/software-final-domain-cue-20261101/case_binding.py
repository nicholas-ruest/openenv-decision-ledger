"""Lazy Native trial binding after the original immutable screen inventory gate.

No execution runner, provider, financial admission or confirmation permission.
Public source remains unsealed and cannot construct a live trial.
"""
import copy
import importlib.util
from pathlib import Path
import live_gate as gate

HERE=Path(__file__).resolve().parent
if Path(gate.__file__).resolve()!=HERE/'live_gate.py':raise ValueError('exact sibling gate required')


def _runtime():
    # Native and tokenizer-free trial machinery is imported only after require_case.
    spec=importlib.util.spec_from_file_location('late_domain_bound_original_protocol',HERE/'matched_protocol.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def materialize(job,args):
    admitted=gate.require_case(args)
    if not isinstance(job,dict) or not any(job==x and gate.digest(job)==gate.digest(x) for x in admitted['jobs']):
        raise ValueError('exact original screen assignment required')
    frozen=copy.deepcopy(job)
    runtime=_runtime()

    class BoundEnvironment(runtime.r.RevisionEnvironment):
        def reset(self,seed=None,episode_id=None,**kwargs):
            if type(seed) is not int or seed!=frozen['seed'] or kwargs!={'task_id':frozen['task_id']}:
                raise ValueError('immutable task and seed binding required')
            return self._initialize(seed,episode_id,kwargs)

    class BoundTrial(runtime.p.Trial):
        def __init__(self):
            self._initialize(frozen,BoundEnvironment(arm=frozen['arm']))
            self.case_audit_sha256=admitted['case_audit_sha256']

    return BoundTrial()
