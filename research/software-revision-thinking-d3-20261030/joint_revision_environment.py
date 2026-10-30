"""Experimental two-response repair candidate. No provider/submission driver."""
from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import Action, State
from pydantic import Field

from repair_env.environment import RepairAction
from repair_env.direct_environment import DirectRepairEnvironment, DirectRepairObservation
from repair_env.tasks import SOURCE_PATH
from repair_env.runner import Program
from public_check import feedback,canonical
from field_feedback import compact

TASKS=('software_repair-ignore-d3',)
ARMS=('field_only','field_contract')


class RevisionAction(Action):
    content:str=Field(default='',max_length=8192,description='Complete proposed Python module. Empty keeps the last module.')
    submit:bool=Field(default=False,description='Submit the current/provided module now. Otherwise first response receives feedback and second is final.')


class RevisionObservation(DirectRepairObservation):
    stage:str=''
    feedback:str=''
    remaining_responses:int=0


class RevisionEnvironment(Environment[RevisionAction,RevisionObservation,State]):
    SUPPORTS_CONCURRENT_SESSIONS=True
    _finish_action=RevisionAction(submit=True)

    def __init__(self,*,arm='field_only'):
        super().__init__()
        if arm not in ARMS:raise ValueError('explicit revision arm required')
        self.arm=arm;self._direct=DirectRepairEnvironment();self._terminal=None;self._steps=0;self._visible=None;self._write_error=''

    def reset(self,seed=None,episode_id=None,**kwargs):
        task=kwargs.get('task_id',TASKS[0])
        if task not in TASKS:raise ValueError('joint revision task only')
        native=self._direct.reset(seed=seed,episode_id=episode_id,task_id=task)
        self._terminal=None;self._steps=0;self._visible={'examples':native.examples};self._write_error=''
        marker='\nRepair the supplied source. Reply once'
        if marker not in native.prompt:raise ValueError('frozen direct instruction contract changed')
        # Both arms receive IDENTICAL first-turn instructions. Arm affects only
        # computed versus neutral feedback after the first proposed module.
        prompt=native.prompt.split(marker)[0]+('\nPropose a complete repaired Python module as one JSON action. '
            'You have at most two responses. Set submit=true to submit immediately; otherwise your first proposal receives a review turn. '
            'Your second response is final. Empty content retains the current module. '
            'Intermediate observations award no reward. Final reward uses the unchanged complete contract and independent hidden cases.')
        return RevisionObservation(task_id=task,prompt=prompt,source=native.source,examples=native.examples,
            stage='proposal',remaining_responses=2,reward=0,done=False)

    def step(self,action:RevisionAction,timeout_s=None,**kwargs):
        if self._visible is None:raise RuntimeError('reset required')
        if self._terminal is not None:return self._terminal.model_copy(deep=True)
        self._steps+=1
        if action.content:
            written=self._direct._core.step(RepairAction(op='write',path=SOURCE_PATH,content=action.content))
            self._write_error=written.error
        terminal=action.submit or self._steps>=2
        if terminal:
            graded=self._direct._core.step(RepairAction(op='submit'))
            self._terminal=RevisionObservation(task_id=self._direct._task.task_id,stage='terminal',done=True,
                reward=0 if self._write_error else graded.reward,error=self._write_error or graded.error,remaining_responses=0)
            return self._terminal.model_copy(deep=True)
        if self.arm in ARMS:
            if self._write_error:result={'kind':'candidate_write_rejected','public_only':True,'hidden_access':False}
            else:result=feedback(self._visible,self._direct._files[SOURCE_PATH],Program)
            result=compact(result)
            if self.arm=='field_contract':
                result['contract_reminder']="Compute each entry and implicit directory's own last-matching-rule status first. Only after ALL rules are resolved, apply the final ancestor-directory statuses to descendants; do not freeze descendant outcomes before later parent negations are resolved."
            text=canonical(result)
        else:text='Review your previous module against the original contract and the supplied examples. No computed test results are provided.'
        return RevisionObservation(task_id=self._direct._task.task_id,stage='revision',feedback=text,remaining_responses=1,reward=0,done=False)

    @property
    def state(self):return self._direct.state.model_copy(update={'step_count':self._steps})
