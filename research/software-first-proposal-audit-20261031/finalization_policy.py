"""Offline controller-policy prototype over an unchanged Native Trial.

Not a live caller, training environment, budget gate or deployment adapter.
The caller must count every returned observation against the original budget.
"""
import copy
import json

from audit import public_pass

ARMS = ('standard_revision', 'public_pass_finalize')


class FinalizationPolicy:
    def __init__(self, trial, *, arm):
        if arm not in ARMS:
            raise ValueError('explicit policy arm required')
        self.trial = trial
        self.arm = arm
        self.model_responses = 0
        self.controller_actions = []

    @property
    def request_messages(self):
        if self.trial.closed:
            raise ValueError('no provider request after terminal finalization')
        return copy.deepcopy(self.trial.messages)

    def consume_model(self, text, *, finish_reason):
        if finish_reason != 'stop':
            raise ValueError('incomplete/provider-failed responses cannot be recovered')
        before = len(self.trial.native)
        result = self.trial.consume(text)
        self.model_responses += 1
        if (self.arm == 'public_pass_finalize' and self.model_responses == 1
                and result.get('category') == 'awaiting_revision' and not result['done']):
            review = self.trial.native[-1]
            if review['done'] or review['reward'] != 0 or review['stage'] != 'revision':
                raise ValueError('unchanged nonterminal zero-reward review required')
            if public_pass(json.loads(review['feedback'])):
                # Decide exclusively from public feedback, before hidden grading.
                action = dict(content='')
                result = self.trial.consume(json.dumps(action))
                if not result['done']:
                    raise ValueError('original empty action must finalize the proposal')
                self.controller_actions.append(dict(action=action,
                    authored_by='controller', generated_tokens=0,
                    trigger='explicit_all_public_examples_pass'))
        return dict(result, model_responses=self.model_responses,
            controller_actions=copy.deepcopy(self.controller_actions),
            new_observations=copy.deepcopy(self.trial.native[before:]),
            is_training=False, model_improvement=False)


def observation_tokens(result, count):
    """Both review and controller final observation consume the same budget."""
    return sum(count(json.dumps(x, sort_keys=True, separators=(',', ':'), allow_nan=False))
               for x in result['new_observations'])
