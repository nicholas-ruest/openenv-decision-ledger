"""Qualification-only late output-domain reminder; no live cases or caller."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[2]
# Load the frozen original wrapper under a distinct module name.
import importlib.util
old=ROOT/'research/software-entry-order-review-20261101'
sys.path.insert(0,str(old))
spec=importlib.util.spec_from_file_location('original_entry_order_revision',old/'revision_environment.py')
original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
ARMS=('common_review','final_domain_reminder')
REMINDER=('For the final module, the returned dictionary must contain exactly the paths explicitly listed in entries, each mapped to a boolean. '
          'Evaluate implicit parent directories internally when needed, but do not return them as additional keys unless they are explicit entries. '
          'This constrains output keys only; satisfy the entire original contract for the boolean decisions.')

class RevisionEnvironment(original.RevisionEnvironment):
    def __init__(self,*,arm):
        if arm not in ARMS:raise ValueError('explicit qualification arm required')
        self.cue_arm=arm
        super().__init__(arm='relation_only')

    def step(self,action,timeout_s=None):
        observation=super().step(action,timeout_s)
        if observation.stage=='revision' and self.cue_arm=='final_domain_reminder':
            value=json.loads(observation.feedback)
            value['final_output_domain_reminder']=REMINDER
            return observation.model_copy(update={'feedback':original.canonical(value)})
        return observation

def materialize(*args,**kwargs):
    raise ValueError('new live cases, source/case lease and caller remain unsealed')

def plan():
    return dict(kind='final_domain_reminder_offline_preparation',arms=list(ARMS),
        baseline='Frozen common relation review; computed result withheld',
        treatment='Same review plus explicit final output-domain constraint',
        qualification_seed=original.QUALIFICATION_SEED,screen_case_selected=False,confirmation_case_selected=False,
        samples_per_arm=4,assignments_per_phase=8,max_requests_per_phase=16,
        limits=original.plan()['limits'],first_prompts_identical=True,first_responses_unmodified=True,
        only_treatment_difference='One reminder field in the final-review observation',
        final_native_grader_unchanged=True,no_controller_code_edits=True,no_output_projection=True,
        comparison_protocol_qualified=False,live_execution_ready=False,new_cases=0,new_model_calls=0,
        model_improvement=False,is_training=False)
