"""Separate unapproved two-response runtime candidate; no provider or submission code."""
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
path=ROOT/'research/software-final-domain-cue-20261101/revision_environment.py'
spec=importlib.util.spec_from_file_location('domain_runtime_qualified_wrapper',path)
qualified=importlib.util.module_from_spec(spec);spec.loader.exec_module(qualified)
from repair_env.direct_environment import DirectRepairAction

FINISH_KEY='decision_ledger_finalize'
FINISH_ACTION=DirectRepairAction(content='',metadata={FINISH_KEY:True})
TASK_ID='software_repair-ignore-d3'

class DomainCueEnvironment(qualified.RevisionEnvironment):
    _finish_action=FINISH_ACTION
    def __init__(self,*,arm='final_domain_reminder'):
        super().__init__(arm=arm)

    def reset(self,seed=None,episode_id=None,**kwargs):
        task=kwargs.pop('task_id',TASK_ID)
        if kwargs or task!=TASK_ID:raise ValueError('declared joint software repair task required')
        # Runtime-native task generation replaces only the offline fixture restriction.
        # Provider execution/admission is not implemented by this environment.
        return self._initialize(seed,episode_id,dict(task_id=task))

    def step(self,action:DirectRepairAction,timeout_s=None):
        if FINISH_KEY not in action.metadata or self._terminal is not None:
            return super().step(action,timeout_s)
        if set(action.metadata)!={FINISH_KEY} or action.metadata[FINISH_KEY] is not True or action.content!='':
            raise ValueError('exact empty finalization action required')
        if self._visible is None:raise RuntimeError('reset required')
        # A trainer finalization before any proposal must return the actual Native
        # grade immediately. It must not leave an intermediate review observation.
        early=self._steps==0
        if early:self._steps=1
        final=super().step(action,timeout_s)
        if early:self._steps=1 # One externally visible finalization, not two actions.
        return final
