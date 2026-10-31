"""Separate fixed action-example comparison. No provider or spending entry point.

Planning does not instantiate Native tasks. Capturing a screen requires the
actual environment; reserved confirmation observations cannot be captured here.
"""
import copy
import hashlib
import json

NAMESPACE = 'action-instance-example-20261030'
TASK = 'software_repair-ignore-d2'
ARMS = ('schema_only', 'action_example')
SEEDS = {'screen': 3100000, 'confirmation': 3110000}
SAMPLING = dict(model='Qwen/Qwen3.8-27B:deepinfra', temperature=0.7,
                response_format=dict(type='json_object'))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def schedule(phase):
    if type(phase) is not str or phase not in SEEDS:
        raise ValueError('explicit frozen phase required')
    jobs = []
    for sample in range(4):
        for arm in ARMS if sample % 2 == 0 else reversed(ARMS):
            identity = dict(namespace=NAMESPACE, phase=phase, task_id=TASK,
                            seed=SEEDS[phase], sample=sample, arm=arm)
            jobs.append(dict(identity, attempt_id=digest(identity)))
    return jobs


def checked_job(job):
    if (type(job) is not dict or type(job.get('seed')) is not int or
            type(job.get('sample')) is not int or job not in schedule(job.get('phase'))):
        raise ValueError('original exact assigned job required')


def sampling_for(job, turn):
    checked_job(job)
    if type(turn) is not int or turn not in (0, 1):
        raise ValueError('two original responses only')
    return copy.deepcopy(SAMPLING)


class Trial:
    def __init__(self, job):
        checked_job(job)
        if job['phase'] != 'screen':
            raise ValueError('confirmation requires separate selected and attested protocol')
        # These imports deliberately require the real pinned Native integration.
        # No scripted fallback is used when that integration is unavailable.
        from action_example_environment import ActionExampleEnvironment, ProposalAction
        from terminal_audit import classify
        self.action_type = ProposalAction
        self.classify = classify
        self.job = copy.deepcopy(job)
        self.env = ActionExampleEnvironment(arm=job['arm'])
        reset = self.env.reset(task_id=job['task_id'], seed=job['seed']).model_dump()
        self.messages = [dict(role='system', content=(
            'Return exactly one JSON action instance matching this schema. '
            'No markdown, diff, or tool command. ' + canonical(ProposalAction.model_json_schema()))),
            dict(role='user', content=canonical(reset))]
        self.turn = 0
        self.closed = False
        self.native = []

    def consume(self, reply):
        from pydantic import ValidationError
        if self.closed or self.turn >= 2:
            raise ValueError('no retry/redraw after terminal')
        self.turn += 1
        try:
            if type(reply) is not str:
                raise ValueError('raw assistant text required')
            action = self.action_type.model_validate_json(reply, strict=True)
        except (ValidationError, ValueError):
            self.closed = True
            return dict(category='format', done=True, native_reward=None, semantic_reward=None)
        obs = self.env.step(action).model_dump()
        self.native.append(obs)
        self.messages += [dict(role='assistant', content=reply),
                          dict(role='user', content=canonical(obs))]
        if obs['done']:
            if self.turn != 2 and action.content:
                raise ValueError('only an empty action may finish before review')
            self.closed = True
            return dict(self.classify(self.env, obs), done=True)
        if (self.turn != 1 or obs['stage'] != 'revision' or
                obs['remaining_responses'] != 1 or obs['reward'] != 0):
            raise ValueError('required review contract changed')
        return dict(category='awaiting_revision', done=False, native_reward=0, semantic_reward=None)


def capture(job):
    if job not in schedule('screen'):
        raise ValueError('confirmation observations remain unmaterialized')
    from action_example_environment import ACTION_EXAMPLE_NOTE
    trial = Trial(job)
    reset = json.loads(trial.messages[1]['content'])
    if job['arm'] == 'action_example':
        if not reset['prompt'].endswith(ACTION_EXAMPLE_NOTE):
            raise ValueError('exact initial treatment note required')
        reset['prompt'] = reset['prompt'][:-len(ACTION_EXAMPLE_NOTE)]
    problem = {k: reset[k] for k in ('task_id', 'prompt', 'source', 'examples')}
    return dict(messages=copy.deepcopy(trial.messages), prompt_sha256=digest(trial.messages),
                problem_sha256=digest(problem))


def plan():
    return dict(namespace=NAMESPACE, task_id=TASK, arms=list(ARMS),
                screen_jobs=schedule('screen'), confirmation_jobs=schedule('confirmation'),
                sampling=copy.deepcopy(SAMPLING), max_attempts=8, max_calls=16,
                max_calls_per_chunk=4, retries=0, first_generation_limit=6000,
                completion_with_observations=8192, context=24576,
                reserved_final_observation_tokens=96, attempt_wall_seconds=600,
                confirmation_observations_materialized=False,
                case_disjointness_verified=False, paid_execution_ready=False,
                selection=('Complete eight original assignments with independently verified usage, '
                           'no provider or budget failure, positive treatment full-solve delta and '
                           'nonnegative semantic delta. Preserve every failure in the denominator. '
                           'Bind the exact treatment-only note before screen execution. '
                           'Freeze selection before unchanged fresh disjoint confirmation.'),
                is_training=False, model_improvement=False, leaderboard_gain=False)


def bundle(chunk):
    if type(chunk) is not int or chunk not in range(4):
        raise ValueError('four original chunks required')
    value = plan()
    jobs = value['screen_jobs']
    arms = {a: capture(next(j for j in jobs if j['arm'] == a)) for a in ARMS}
    if arms[ARMS[0]]['problem_sha256'] != arms[ARMS[1]]['problem_sha256']:
        raise ValueError('original problem must match exactly')
    if arms[ARMS[0]]['prompt_sha256'] == arms[ARMS[1]]['prompt_sha256']:
        raise ValueError('initial action-example intervention required')
    value.update(chunk=chunk, all_screen_jobs=jobs,
                 screen_jobs=[j for j in jobs if j['sample'] == chunk],
                 screen_groups=[dict(task_id=TASK, seed=SEEDS['screen'],
                                     problem_sha256=arms[ARMS[0]]['problem_sha256'], arms=arms)])
    return value
