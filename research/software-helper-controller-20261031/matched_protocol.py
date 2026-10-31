"""Matched helper-preservation adapter and qualification traces. No provider API.

Future case identities are planning metadata only. Production materialization
remains sealed off until a separate immutable private case/admission lease.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'research/software-action-example-20261030'),
               str(ROOT/'integrations/openenv-arena'),
               str(ROOT/'integrations/software-repair')]
from helper_policy import HelperPreservationPolicy

ARMS = ('standard_revision', 'preserve_declared_helpers')
TASK = 'software_repair-ignore-d2'
SEEDS = dict(screen=3140000, confirmation=3150000)
SAMPLING = dict(model='Qwen/Qwen3.8-27B:deepinfra', temperature=0.7,
                response_format=dict(type='json_object'))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def jobs(phase):
    if phase not in ('screen', 'confirmation', 'qualification'):
        raise ValueError('explicit phase required')
    seed = 3100000 if phase == 'qualification' else SEEDS[phase]
    result = []
    for sample in range(4):
        for arm in ARMS if sample % 2 == 0 else reversed(ARMS):
            value = dict(namespace='declared-helper-controller-20261031', phase=phase,
                         task_id=TASK, seed=seed, sample=sample, arm=arm)
            result.append(dict(value, attempt_id=digest(value)))
    return result


def plan():
    return dict(screen_jobs=jobs('screen'), confirmation_jobs=jobs('confirmation'),
        sampling=copy.deepcopy(SAMPLING), max_attempts=8, max_calls=16,
        first_generation_limit=6000, completion_with_observations=8192,
        context=24576, final_observation_reserve=96, retries=0,
        paid_execution_ready=False, live_case_lease=None,
        screen_materialized=False, confirmation_materialized=False,
        outcome_scope='model_plus_controller_system_attempts', is_training=False)


def materialize(job):
    # No environment variable, boolean, CLI option or qualification flag can
    # turn planning identities into a live Native case in this source revision.
    raise ValueError('unsealed live case lease; production materialization refused')


class QualificationTrial:
    def __init__(self, job):
        if job not in jobs('qualification'):
            raise ValueError('existing qualification case only')
        from action_example_protocol import Trial, schedule
        original = Trial(schedule('screen')[0])
        self.policy = HelperPreservationPolicy(original, arm=job['arm'])

    @property
    def messages(self):
        return copy.deepcopy(self.policy.trial.messages)

    def consume(self, text):
        return self.policy.consume_model(text, finish_reason='stop')


def observe_scripted(job, responses, counter):
    """Produce a qualification trace; scripted labels cannot become live proof."""
    trial = QualificationTrial(job)
    trace = dict(job=copy.deepcopy(job), scripted=True, events=[])
    generation = native = controller = 0
    category = 'budget'
    for turn, response in enumerate(responses):
        if turn >= 2:
            raise ValueError('two responses only; no retry')
        limit = 6000 if turn == 0 else 8192-generation-native-controller-96
        usage = response['usage']
        if any(type(usage.get(k)) is not int or usage[k] < 0 for k in ('prompt_tokens', 'completion_tokens')):
            raise ValueError('known original generation usage required')
        if not 0 < limit or usage['completion_tokens'] > limit or usage['prompt_tokens']+usage['completion_tokens'] > 24576:
            raise ValueError('unchanged budgets exceeded')
        event = dict(response=copy.deepcopy(response), prompt_sha256=digest(trial.messages),
                     requested_max_tokens=limit)
        generation += usage['completion_tokens']
        finish = response['choices'][0]['finish_reason']
        if finish == 'length':
            category = 'truncation'
            event['native_observations'] = []; event['controller_observations'] = []
            event['controller_actions'] = copy.deepcopy(trial.policy.controller_actions)
            trace['events'].append(event)
            break
        if finish != 'stop':
            raise ValueError('explicit provider failure handling required before live use')
        result = trial.consume(response['choices'][0]['message']['content'])
        event.update(native_observations=result['new_observations'],
                     controller_observations=result['controller_observations'],
                     controller_actions=result['controller_actions'])
        native += sum(counter.count(canonical(x)) for x in event['native_observations'])
        controller += sum(counter.count(canonical(x)) for x in event['controller_observations'])
        if generation+native+controller > 8192 or counter.context(trial.messages) > 24576:
            raise ValueError('all Native/controller observations must fit original budgets')
        trace['events'].append(event)
        category = result['category']
        if result['done']:
            break
    trace['record'] = dict(category=category, generation_tokens=generation,
        native_observation_tokens=native, controller_observation_tokens=controller,
        completion_with_observations=generation+native+controller,
        model_responses=len(trace['events']), controller_actions=copy.deepcopy(trial.policy.controller_actions),
        model_response_only_full=category=='full' and not trial.policy.controller_actions,
        controller_assisted_full=category=='full' and bool(trial.policy.controller_actions))
    return trace
