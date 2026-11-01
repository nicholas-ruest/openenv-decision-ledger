"""Frozen matched schedule and independent qualification replay. No paid API."""
import copy
import preserve_first as native

ARMS = native.ARMS
SEEDS = dict(qualification=native.QUALIFICATION_SEED, screen=3180000, confirmation=3190000)
NAMESPACE = 'preserve-first-action-20261101'


def jobs(phase):
    if phase not in SEEDS:
        raise ValueError('explicit phase required')
    rows = []
    for sample in range(4):
        for arm in ARMS if sample % 2 == 0 else reversed(ARMS):
            identity = dict(namespace=NAMESPACE, phase=phase, seed=SEEDS[phase],
                            task_id=native.TASK, sample=sample, arm=arm)
            rows.append(dict(identity, attempt_id=native.digest(identity)))
    return rows


def plan():
    return dict(screen_jobs=jobs('screen'), confirmation_jobs=jobs('confirmation'),
        sampling=copy.deepcopy(native.SAMPLING), limits=native.limits(),
        max_assignments=8, max_requests=8, confirmation_materialized=False,
        live_execution_ready=False, paid_calls=0,
        selection='All eight original assignments independently replayed with known usage; positive treatment full-outcome count delta and nonnegative mean semantic delta; no provider, execution or budget failures. Then require unchanged fresh disjoint confirmation; never pool selected screen with confirmation.',
        inference_unit='one procedural case per phase; four samples per arm are repeated model draws, not independent cases')


def observe_scripted(job, response, counter):
    if job not in jobs('qualification'):
        raise ValueError('already-seen qualification assignments only')
    trial = native.QualificationTrial(native.qualification_job(job['arm']))
    initial = copy.deepcopy(trial.messages)
    payload = dict(copy.deepcopy(native.SAMPLING), messages=initial, max_tokens=6000)
    usage = response.get('usage', {})
    choices = response.get('choices')
    if (not isinstance(response.get('id'), str) or not response['id']
        or any(type(usage.get(k)) is not int or usage[k] < 0
               for k in ('prompt_tokens', 'completion_tokens'))
        or not isinstance(choices, list) or len(choices) != 1):
        raise ValueError('unique reply identity and actual known usage required')
    if (usage['completion_tokens'] > 6000 or usage['prompt_tokens'] > 28672
        or usage['prompt_tokens'] + usage['completion_tokens'] > 24576
        or counter.context(initial) + 6000 + 96 > 24576):
        raise ValueError('original generation/context limits exceeded')
    choice = choices[0]
    result = trial.consume(choice.get('message', {}).get('content'),
                           finish_reason=choice.get('finish_reason'))
    observations = result['new_observations']
    tokens = sum(counter.count(native.canonical(x)) for x in observations)
    if (usage['completion_tokens'] + tokens > 8192
        or counter.context(trial.messages) > 24576):
        raise ValueError('actual observations exceed original budget')
    record = dict(category=result['category'], semantic_reward=result['semantic_reward'],
        terminal_reward_observed=result['native_reward'], generation_tokens=usage['completion_tokens'],
        native_observation_tokens=tokens, completion_with_observations=usage['completion_tokens'] + tokens,
        model_responses=1, finish_reason=choice.get('finish_reason'), controller_actions=[])
    return dict(job=copy.deepcopy(job), scripted=True, live_evidence=False,
        request_sha256=native.digest(payload), prompt_sha256=native.digest(initial),
        problem_sha256=trial.binding.problem_sha256, response=copy.deepcopy(response),
        observations=observations, messages=trial.messages, record=record)


def verify(trace, counter):
    if trace.get('scripted') is not True or trace.get('live_evidence') is not False:
        raise ValueError('qualification must not be relabelled as live evidence')
    expected = observe_scripted(trace['job'], trace['response'], counter)
    if trace != expected:
        raise ValueError('request, reply, Native grade or token accounting changed')
    return dict(job=trace['job'], verified=True, scripted=True, live_evidence=False,
                **expected['record'])


def verify_phase(traces, counter):
    if len(traces) != 8 or [t['job'] for t in traces] != jobs('qualification'):
        raise ValueError('all eight counterbalanced original assignments required')
    identities = [t['response']['id'] for t in traces]
    if len(set(identities)) != 8:
        raise ValueError('cross-attempt response reuse')
    rows = [verify(t, counter) for t in traces]
    if len({t['problem_sha256'] for t in traces}) != 1:
        raise ValueError('matched Native problem required')
    for arm in ARMS:
        if len({t['prompt_sha256'] for t in traces if t['job']['arm'] == arm}) != 1:
            raise ValueError('fixed arm-specific first prompt required')
    if traces[0]['prompt_sha256'] == traces[1]['prompt_sha256']:
        raise ValueError('original guidance contrast missing')
    return dict(kind='preserve_first_qualification', scripted=True, live_evidence=False,
        assigned=8, all_assigned_in_denominator=True, rows=rows,
        selection_passed=False, model_improvement=False, leaderboard_gain=False)
