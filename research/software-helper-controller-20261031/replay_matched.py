"""Independent Native/controller replay with distinct qualification and sealed-screen entries."""
import copy
from matched_protocol import QualificationTrial, canonical, digest, jobs


def verify(trace, counter):
    if trace.get('scripted') is not True or trace['job'] not in jobs('qualification'):
        raise ValueError('qualification replay is not live evidence')
    return _verify(trace,counter,QualificationTrial(trace['job']),True)


def verify_screen(trace,counter,case_audit,case_sha256):
    from matched_protocol import materialize
    from screen_materializer import execution_hashes
    if (trace.get('scripted') is not False or trace['job'] not in jobs('screen')
            or trace.get('case_audit_sha256')!=case_sha256 or trace.get('execution_sha256')!=execution_hashes()):
        raise ValueError('exact sealed live screen trace required')
    result=_verify(trace,counter,materialize(trace['job'],case_audit,case_sha256),False)
    return dict(result,case_audit_sha256=case_sha256)


def _verify(trace,counter,trial,scripted):
    events = trace['events']
    if not 1 <= len(events) <= 2:
        raise ValueError('original two-response schedule required')
    generated = native = receipts = 0
    category = None
    terminal = False
    last_result = None
    for turn, e in enumerate(events):
        if terminal or e['prompt_sha256'] != digest(trial.messages):
            raise ValueError('actual model transcript changed or resumed')
        limit = 6000 if turn == 0 else 8192-generated-native-receipts-96
        r = e['response']; u = r['usage']
        if (e['requested_max_tokens'] != limit or any(type(u.get(k)) is not int or u[k]<0 for k in ('prompt_tokens','completion_tokens'))
                or not 0 < limit or u['completion_tokens'] > limit or u['prompt_tokens']>28672
                or counter.context(trial.messages)+limit+96>24576
                or not isinstance(r.get('choices'),list) or len(r['choices'])!=1
                or u['prompt_tokens']+u['completion_tokens'] > 24576):
            raise ValueError('original usage/budget differs')
        generated += u['completion_tokens']
        choice = r['choices'][0]
        if choice['finish_reason'] == 'length':
            if e['native_observations'] or e['controller_observations'] or e['controller_actions'] != trial.policy.controller_actions:
                raise ValueError('truncated response cannot produce a controller recovery')
            category = 'truncation'; terminal = True
            continue
        if choice['finish_reason'] != 'stop':
            raise ValueError('unsupported provider outcome')
        result = trial.consume(choice['message']['content'])
        last_result = result
        if (e['native_observations'] != result['new_observations']
                or e['controller_observations'] != result['controller_observations']
                or e['controller_actions'] != result['controller_actions']):
            raise ValueError('Native/controller provenance differs')
        native += sum(counter.count(canonical(x)) for x in result['new_observations'])
        receipts += sum(counter.count(canonical(x)) for x in result['controller_observations'])
        if generated+native+receipts > 8192 or counter.context(trial.messages) > 24576:
            raise ValueError('observation/context budget exceeded')
        category = result['category']; terminal = result['done']
    if not terminal:
        raise ValueError('incomplete trace cannot be an assigned outcome')
    expected = dict(category=category, generation_tokens=generated,
        native_observation_tokens=native, controller_observation_tokens=receipts,
        completion_with_observations=generated+native+receipts, model_responses=len(events),
        controller_actions=copy.deepcopy(trial.policy.controller_actions),
        model_response_only_full=category=='full' and not trial.policy.controller_actions,
        controller_assisted_full=category=='full' and bool(trial.policy.controller_actions))
    if trace['record'] != expected:
        raise ValueError('outcome or accounting differs from independent replay')
    reward=last_result.get('semantic_reward') if last_result and category in ('full','partial','wrong') else None
    terminal_reward=last_result.get('native_reward') if last_result and last_result['done'] else None
    return dict(verified=True, scripted=scripted, live_evidence=not scripted,
        semantic_reward=reward, terminal_reward_observed=terminal_reward,
        finish_reason=events[-1]['response']['choices'][0]['finish_reason'], **expected)
