"""Fixed same-prompt public-pass finalization comparison. No paid entry point.

Planning does not instantiate Native tasks. Capturing a screen requires the
actual environment; reserved confirmation observations cannot be captured here.
"""
import copy
import hashlib
import json

NAMESPACE = 'public-pass-finalize-20261031'
TASK = 'software_repair-ignore-d2'
ARMS = ('standard_revision', 'public_pass_finalize')
SEEDS = {'screen': 3120000, 'confirmation': 3130000}
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
        from pathlib import Path
        import sys
        root=Path(__file__).resolve().parents[2]
        sys.path[:0]=[str(root/'research/software-action-example-20261030'),
                     str(root/'research/software-first-proposal-audit-20261031')]
        from action_example_protocol import Trial as OriginalTrial
        from action_example_environment import ActionExampleEnvironment, ProposalAction
        from terminal_audit import classify
        from finalization_policy import FinalizationPolicy
        # Reuse the original consume/parser/grade implementation. Only reset the
        # original baseline environment with this explicitly checked assignment.
        base=object.__new__(OriginalTrial)
        base.action_type=ProposalAction; base.classify=classify; base.job=copy.deepcopy(job)
        base.env=ActionExampleEnvironment(arm='schema_only')
        reset=base.env.reset(task_id=job['task_id'],seed=job['seed']).model_dump()
        base.messages=[dict(role='system',content=(
            'Return exactly one JSON action instance matching this schema. '
            'No markdown, diff, or tool command. '+canonical(ProposalAction.model_json_schema()))),
            dict(role='user',content=canonical(reset))]
        base.turn=0; base.closed=False; base.native=[]
        self.policy=FinalizationPolicy(base,arm=job['arm'])
    @property
    def messages(self): return copy.deepcopy(self.policy.trial.messages)
    @property
    def turn(self): return self.policy.model_responses
    @property
    def native(self): return self.policy.trial.native
    @property
    def closed(self): return self.policy.trial.closed
    def consume(self, reply): return self.policy.consume_model(reply,finish_reason='stop')


def capture(job):
    if job not in schedule('screen'):
        raise ValueError('confirmation observations remain unmaterialized')
    trial=Trial(job); reset=json.loads(trial.messages[1]['content'])
    problem={k:reset[k] for k in ('task_id','prompt','source','examples')}
    return dict(messages=trial.messages,prompt_sha256=digest(trial.messages),problem_sha256=digest(problem))


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
                           'Bind the public-only controller decision before screen execution. '
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
    if arms[ARMS[0]]['prompt_sha256'] != arms[ARMS[1]]['prompt_sha256']:
        raise ValueError('identical initial prompts required')
    value.update(chunk=chunk, all_screen_jobs=jobs,
                 screen_jobs=[j for j in jobs if j['sample'] == chunk],
                 screen_groups=[dict(task_id=TASK, seed=SEEDS['screen'],
                                     problem_sha256=arms[ARMS[0]]['problem_sha256'], arms=arms)])
    return value
