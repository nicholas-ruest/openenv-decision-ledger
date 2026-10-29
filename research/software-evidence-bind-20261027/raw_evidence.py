"""Offline raw-response/reservation binding; no network, spending or promotion.

Legacy ledgers prove identity/amount agreement, not reservation chronology or
provider dispatch. Replaying a saved answer is an oracle control, not a new solve.
"""
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def amount(value):
    if isinstance(value, bool):
        raise ValueError('numeric reservation required')
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('numeric reservation required') from exc
    if not result.is_finite() or result < 0 or not math.isfinite(float(result)):
        raise ValueError('finite nonnegative reservation required')
    return result


def bind(jobs, records, reservations, runtime, settings_sha, capture, replay, classify):
    """Rebuild normalized evidence from complete persisted job envelopes.

    Each job binds arm/task/seed/sample/planned_call_label to raw returned fields.
    capture(arm,task,seed) must produce a *fresh frozen native* snapshot.
    replay(arm,task,seed,assistant_message) must run the saved action natively.
    For transcripts ending in an environment observation, return both reward and
    observation; otherwise a scalar native reward is accepted.
    Callers must attest source/policy dependencies separately. No file is edited.
    """
    if runtime != "0b8ccc3ca70a67fed5fc5837b69022261cc60497" or not isinstance(settings_sha,str) or len(settings_sha)!=64 or any(c not in "0123456789abcdef" for c in settings_sha):
        raise ValueError("frozen runtime and settings SHA required")
    ledger = {}
    for row in reservations:
        label = row.get('label')
        if not isinstance(label,str) or not label or label in ledger:
            raise ValueError('unique ledger labels required')
        amount(row['usd'])
        ledger[label] = row
    keys, labels, responses, rebuilt, snapshots = set(), set(), set(), [], {}
    reserved_jobs = observed = replayed = 0
    if len(jobs) != len(records) or not jobs:
        raise ValueError('complete nonempty raw and normalized archives required')
    for job in jobs:
        key = tuple(job[k] for k in ('arm','task_id','seed','sample'))
        label = job['planned_call_label']
        if type(key[2]) is not int or type(key[3]) is not int or key[3] not in range(4):
            raise ValueError('integer seeded sample required')
        if key in keys or not isinstance(label,str) or not label or label in labels:
            raise ValueError('independent unique jobs and planned labels required')
        keys.add(key); labels.add(label)
        raw = job['raw']
        if type(raw['seed']) is not int or type(raw['sample']) is not int or any(raw[k] != job[k] for k in ('task_id','seed','sample')):
            raise ValueError('raw sample differs from job identity')
        group = key[:3]
        if group not in snapshots:
            snapshots[group] = capture(*group)
        expected = snapshots[group]
        messages = raw.get('messages',[])
        if messages[:2] != expected['messages'] or raw.get('prompt_sha256') != expected['base_prompt_sha256']:
            raise ValueError('actual request differs from fresh reset/policy snapshot')
        # Recompute actual request/reset/workspace hashes rather than copying claims.
        if (digest(messages[:2]) != expected['prompt_sha256'] or
            digest(expected['files']) != expected['workspace_sha256'] or
            digest(expected['reset']) != expected['reset_sha256']):
            raise ValueError('snapshot content/hash mismatch')
        calls = raw.get('calls')
        if not isinstance(calls,list) or len(calls)>1:
            raise ValueError('one-call protocol required')
        failure = classify(raw)
        reserved = ledger.get(label)
        if reserved is not None: reserved_jobs += 1
        response = None
        if calls:
            observed += 1
            call = calls[0]
            if call['client_call_label'] != label or reserved is None:
                raise ValueError('observed response lacks its exact reservation')
            # Writer returns float(amount); accept only the same float projection,
            # not a broad epsilon that can conceal a changed reservation.
            if float(amount(reserved['usd'])) != float(amount(call['reserved_usd'])):
                raise ValueError('reservation amount differs from observed metric')
            response = call.get('provider_response_id_sha256')
            if response is not None:
                if not isinstance(response,str) or len(response)!=64 or any(c not in '0123456789abcdef' for c in response) or response in responses:
                    raise ValueError('complete independent response hashes required')
                responses.add(response)
        reward = raw.get('reward')
        if failure is None:
            if not calls or response is None or len(messages) not in (3,4) or messages[2].get('role')!='assistant' or (len(messages)==4 and messages[3].get('role')!='user'):
                raise ValueError('valid result needs actual saved assistant response')
            if type(reward) not in (int,float) or not math.isfinite(reward) or not 0<=reward<=1:
                raise ValueError('finite semantic reward required')
            if call.get('finish_reason') != 'stop':
                raise ValueError('semantic result needs a complete provider response')
            for usage,bound in (('prompt_tokens','prompt_bound'),('completion_tokens','generation_bound')):
                if type(call.get(usage)) is not int or type(reserved.get(bound)) is not int or not 0<=call[usage]<=reserved[bound]:
                    raise ValueError('valid result needs usage within its reservation')
            native = replay(*group,messages[2])
            if len(messages)==4:
                if not isinstance(native,dict) or json.loads(messages[3]['content']) != native.get('observation'):
                    raise ValueError('saved environment observation differs from native replay')
            native_reward = native.get('reward') if isinstance(native,dict) else native
            if type(native_reward) not in (int,float) or not math.isfinite(native_reward) or native_reward != reward:
                raise ValueError('saved answer native reward mismatch')
            replayed += 1
        elif failure not in {'format','provider','truncation','execution','budget'}:
            raise ValueError('unknown failure classification')
        row = {'arm':key[0], 'task_id':key[1], 'seed':key[2], 'sample':key[3],
               'runtime_source':runtime,'settings_sha256':settings_sha,
               **{k:expected[k] for k in ('case_sha256','reset_sha256','workspace_sha256','prompt_sha256')},
               'client_call_label':label,'provider_response_id_sha256':response,
               'provider_call_observed':bool(calls),'failure':failure,'reward':reward}
        rebuilt.append(row)
    # Full exact normalized comparison: ordering is the durable dispatch order.
    if rebuilt != records:
        raise ValueError('normalized records differ from raw evidence')
    return {'raw_records':len(jobs),'observed_response_records':observed,
            'reserved_jobs':reserved_jobs,'reservation_only_jobs':reserved_jobs-observed,
            'unreserved_jobs':len(jobs)-reserved_jobs,'native_replayed_valid_answers':replayed,
            'groups':len(snapshots),'raw_sha256':digest(jobs),'records_sha256':digest(records),
            'reservation_ledger_sha256':digest(reservations),
            'reservation_order_attested':False,'provider_dispatch_attested':False,
            'provider_response_authenticity_attested':False,
            'is_training':False,'model_improvement_claim':False,'promotion':False}
