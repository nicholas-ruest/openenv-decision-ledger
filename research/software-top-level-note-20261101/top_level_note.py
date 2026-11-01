"""Qualification-only initial syntax guidance; original Native grader unchanged."""
import copy
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research/software-preserve-first-action-20261101'))
import preserve_first as original

ARMS=('baseline','top_level_only')
NOTE=('\nImplementation constraint: define every function at module level. '
      'If the repair needs a helper, place its def alongside the supplied functions; '
      'do not put a def inside another function. Return the complete module. '
      'This restates the declared Python subset and does not change the task contract or scoring.')


def job(arm):
    if arm not in ARMS:raise ValueError('explicit declared arm required')
    return dict(namespace='top-level-note-20261101',phase='qualification',
                task_id=original.TASK,seed=original.QUALIFICATION_SEED,arm=arm)


def outcome_origin(result,native):
    """Analysis metadata only: never spending, continuation or selection authority.

    Verified program rejection is distinct from an exception raised by Native
    stepping. Caller still needs known actual usage and independent raw replay.
    """
    category=result['category']
    if category in ('full','partial','wrong'):
        if not native or native.get('done') is not True:
            raise ValueError('observed terminal Native result required')
        return 'native_semantic_outcome'
    if category=='execution':
        if native and native.get('done') is True:
            if result.get('compile_rejected') is True:return 'model_program_rejection'
            if type(result.get('hidden_execution_errors')) is int and result['hidden_execution_errors']>0:
                return 'model_program_runtime_error'
        return 'native_execution_unverified'
    if category in ('format','truncation'):return 'model_output_'+category
    if category in ('provider','budget'):return category+'_failure'
    raise ValueError('unknown outcome category')


class Binding(original.QualificationBinding):
    def __init__(self,current):
        if current!=job(current.get('arm')):raise ValueError('already-seen qualification input only')
        # Use the proven original Native binding in its unmodified baseline arm.
        # No helper-preservation or public-example self-check cue is inherited.
        self._reset(current['task_id'],current['seed'],'baseline')
        if current['arm']=='top_level_only':
            observation=json.loads(self.messages[1]['content'])
            observation['prompt']+=NOTE
            self.messages[1]['content']=original.canonical(observation)
        self.prompt_sha256=original.digest(self.messages)


class QualificationTrial(original.QualificationTrial):
    def __init__(self,current):
        frozen=Binding(current)
        original.original.Trial.__init__(self,current,frozen.prompt_sha256,
                                       frozen.problem_sha256,binding_factory=Binding)

    def consume(self,reply,*,finish_reason):
        result=super().consume(reply,finish_reason=finish_reason)
        self.last_outcome=dict(result,failure_origin=outcome_origin(result,self.native))
        return copy.deepcopy(self.last_outcome)


def materialize(*args,**kwargs):
    raise ValueError('new screen/confirmation inputs and paid execution are unsealed')


def plan():
    return dict(kind='top_level_note_preparation',arms=ARMS,
        namespace='top-level-note-20261101',task_id=original.TASK,
        planning_seeds=dict(screen=3200000,confirmation=3210000),
        max_assignments_per_phase=8,samples_per_arm=4,
        sampling=copy.deepcopy(original.SAMPLING),limits=original.limits(),
        initial_guidance=NOTE,helper_preservation_cue=False,public_example_selfcheck_cue=False,
        new_cases=0,new_model_calls=0,live_execution_ready=False,
        outcome_taxonomy_is_analysis_only=True,live_continuation_policy_frozen=False,
        confirmation_materialized=False,model_improvement=False,is_training=False)
