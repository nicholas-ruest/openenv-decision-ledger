"""Qualification-only two-response relation feedback; original final Native grade."""
from order_diagnostic import ARMS,RELATION,review,canonical
from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State
from repair_env.environment import RepairAction
from repair_env.direct_environment import DirectRepairEnvironment,DirectRepairAction,DirectRepairObservation
from repair_env.tasks import SOURCE_PATH

QUALIFICATION_SEED=2560000


class Observation(DirectRepairObservation):
    stage:str=''
    feedback:str=''
    remaining_responses:int=0


class RevisionEnvironment(Environment[DirectRepairAction,Observation,State]):
    SUPPORTS_CONCURRENT_SESSIONS=True
    def __init__(self,*,arm):
        super().__init__()
        if arm not in ARMS:raise ValueError('explicit frozen arm required')
        self.arm=arm;self._direct=DirectRepairEnvironment();self._visible=None;self._steps=0;self._terminal=None;self._write_error=''

    def reset(self,seed=None,episode_id=None,**kwargs):
        if kwargs!={'task_id':'software_repair-ignore-d3'} or seed!=QUALIFICATION_SEED:
            raise ValueError('already-seen qualification input only; live cases unsealed')
        return self._initialize(seed,episode_id,kwargs)

    def _initialize(self,seed,episode_id,kwargs):
        native=self._direct.reset(seed=seed,episode_id=episode_id,**kwargs)
        self._visible={'task_id':native.task_id,'examples':native.examples};self._steps=0;self._terminal=None;self._write_error=''
        marker='\nRepair the supplied source. Reply once'
        if marker not in native.prompt:raise ValueError('original Native prompt contract changed')
        prompt=native.prompt.split(marker)[0]+('\nPropose a complete repaired module as one JSON action. You have two responses. '
            'Your first proposal receives a review turn; your second response is final. Empty content retains the previous module. '
            'Intermediate observations award no reward. The final unchanged Native grader uses the complete contract. '+RELATION)
        return Observation(task_id=native.task_id,prompt=prompt,source=native.source,examples=native.examples,
            stage='proposal',remaining_responses=2,reward=0,done=False)

    def step(self,action:DirectRepairAction,timeout_s=None):
        if self._visible is None:raise RuntimeError('reset required')
        if self._terminal is not None:return self._terminal.model_copy(deep=True)
        self._steps+=1
        if action.content:
            written=self._direct._core.step(RepairAction(op='write',path=SOURCE_PATH,content=action.content));self._write_error=written.error
        if self._steps==1:
            if self._write_error:
                value=dict(kind='candidate_write_rejected',public_only=True)
            else:value=review(self._visible,self._direct._files[SOURCE_PATH],self.arm)
            return Observation(task_id=self._visible['task_id'],stage='revision',feedback=canonical(value),remaining_responses=1,reward=0,done=False)
        graded=self._direct._core.step(RepairAction(op='submit'))
        self._terminal=Observation(task_id=self._visible['task_id'],stage='terminal',done=True,
            reward=0 if self._write_error else graded.reward,error=self._write_error or graded.error,remaining_responses=0)
        return self._terminal.model_copy(deep=True)

    @property
    def state(self):return self._direct.state.model_copy(update={'step_count':self._steps})


def materialize(*args,**kwargs):raise ValueError('live source/case lease and caller unsealed')


def plan():
    return dict(kind='public_entry_order_review_preparation',arms=list(ARMS),task_id='software_repair-ignore-d3',
        planning_seeds=dict(screen=3220000,confirmation=3230000),samples_per_arm=4,assignments=8,max_requests=16,
        first_prompts_identical=True,relation_reminder_identical=True,only_treatment_difference='computed public-example entry-permutation diagnostic exposure on review turn',
        no_reference_answers_in_diagnostic=True,original_final_native_grade=True,new_cases=0,new_model_calls=0,
        limits=dict(first_generation=6000,completion_plus_all_observations=8192,context=24576,terminal_reserve=96,request_seconds=360,attempt_seconds=600,whole_phase_seconds=1200),
        feedback_tokens_must_be_counted=True,live_execution_ready=False,confirmation_materialized=False,model_improvement=False,is_training=False)
