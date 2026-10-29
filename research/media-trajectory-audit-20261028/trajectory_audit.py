"""Read-only media trajectory audit. Never sends a provider request or executes actions.

Native replay is an injected trusted image/TCP adapter. Input hashes bind records;
they do not authenticate a provider or prove dispatch/reservation chronology.
"""
import json
import math
from collections import Counter
from decimal import Decimal, InvalidOperation

from media_protocol import IMAGE, RUNTIME, SAMPLING, digest, messages


FAILURES = ('format', 'provider', 'truncation', 'execution', 'budget')
PLAN_BODY_SHA256 = '7eb33f5730d0eada06967b0778d79d20f647dc903803ef3f867118b394e1465f'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    def invalid(_):
        raise ValueError('nonfinite JSON constant')
    require(isinstance(text, str) and len(text.encode()) <= 131072, 'bounded raw reply required')
    try:
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)
        json.dumps(value, allow_nan=False)  # also rejects 1e309 overflow in metadata
        return value
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError('invalid JSON action') from exc


def action_from_reply(text, schema):
    """Validate this frozen flat action schema, not arbitrary future JSON Schema."""
    require(digest(schema) == schema_digest(), 'unsupported frozen schema')
    action = strict_json(text)
    require(isinstance(action, dict), 'action object required')
    properties = schema['action']['properties']
    require(set(action) <= set(properties), 'unknown action property')
    require(set(schema['action']['required']) <= set(action), 'missing action property')
    for key, value in action.items():
        if key == 'metadata':
            require(isinstance(value, dict), 'metadata object required')
        else:
            require(isinstance(value, str), 'string action property required')
        if 'enum' in properties[key]:
            require(value in properties[key]['enum'], 'unknown action type')
    return action


def schema_digest():
    # Set from preserved actual TCP /schema, never from a caller-selected plan.
    return 'f756772d59ca78d8f271302df3e94fb757c75c9629705cb5fb04d7fd6092af4f'


def inspect_transport(value):
    require(isinstance(value, dict) and type(value.get('done')) is bool, 'native outer done required')
    reward = value.get('reward')
    require(type(reward) in (int, float) and math.isfinite(reward) and reward in (0, 1), 'binary native reward required')
    obs = value.get('observation')
    require(isinstance(obs, dict) and type(obs.get('success')) is bool, 'native observation success required')
    require(isinstance(obs.get('error'), str) and isinstance(obs.get('output'), str), 'native error/output strings required')
    if not value['done']:
        require(reward == 0, 'nonterminal reward must remain zero')
    return obs


def audit_episode(episode, plan, schema, reservations, replay):
    """Return classification and local evidence digest; malformed evidence raises.

    One event per attempted call or local budget stop. No retries. A call failure
    is distinct from missing/invalid evidence. Replay receives *validated* actions
    and must return fresh native reset/workspace plus one observation per action.
    """
    require(digest(plan) == PLAN_BODY_SHA256, 'unchanged native-derived protocol required')
    require(plan['image'] == IMAGE and plan['runtime_source'] == RUNTIME, 'frozen runtime required')
    require(plan['sampling'] == SAMPLING and plan['sampling_sha256'] == digest(SAMPLING), 'frozen settings required')
    require(plan['schema_sha256'] == digest(schema) == schema_digest(), 'frozen schema required')
    require(episode['image'] == IMAGE and episode['runtime_source'] == RUNTIME and episode['uid_shell'] is True, 'episode runtime/UID shell required')
    require(episode['sampling_sha256'] == plan['sampling_sha256'], 'episode settings mismatch')
    phase = episode['phase']
    require(phase in plan['phases'] and integer(episode['sample']) and episode['sample'] < 4, 'planned phase/sample required')
    require(integer(episode['seed']), 'integer seed required')
    rows = [r for r in plan['phases'][phase]['groups'] if (r['task_id'], r['seed']) == (episode['task_id'], episode['seed'])]
    require(len(rows) == 1, 'planned task/seed required')
    group = rows[0]
    reset, workspace = episode['reset_transport'], episode['workspace']
    inspect_transport(reset)
    require(not reset['done'] and reset['observation']['success'], 'successful native reset required')
    require(digest(reset) == group['reset_sha256'] and digest(workspace) == group['workspace_sha256'], 'native reset/workspace mismatch')
    require(digest(messages(reset, schema)) == group['prompt_sha256'], 'initial prompt mismatch')
    require(digest({'reset_sha256': digest(reset), 'workspace_sha256': digest(workspace)}) == group['case_sha256'], 'case identity mismatch')
    events = episode['events']
    require(isinstance(events, list) and 1 <= len(events) <= 33, 'bounded nonempty event stream required')
    ledger = {}
    for row in reservations:
        require(isinstance(row['label'], str) and row['label'] and row['label'] not in ledger, 'unique reservation labels required')
        require(integer(row['prompt_bound'], 1) and integer(row['generation_bound'], 1), 'positive reservation token bounds required')
        try:
            amount = Decimal(row['usd'])
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError('finite nonnegative reservation required') from exc
        require(amount.is_finite() and amount >= 0, 'finite nonnegative reservation required')
        ledger[row['label']] = row
    history = messages(reset, schema)
    actions, transports, call_ids, reply_ids, labels = [], [], [], [], []
    generation = 0
    category, detail, semantic, terminal_reward = None, None, None, None
    for index, event in enumerate(events):
        require(category is None, 'events after stop/terminal are forbidden')
        if event['kind'] == 'budget':
            # Explicit local pre-dispatch stop, no forged provider/native evidence.
            require(set(event) == {'kind', 'reason'} and event['reason'] in ('context', 'generation', 'actions', 'deadline'), 'explicit bounded local stop required')
            category, detail = 'budget', event['reason']
            continue
        require(event['kind'] == 'call', 'call or budget event required')
        require(len(actions) < SAMPLING['max_actions'], 'call after action limit')
        call_id, label = event['call_id_sha256'], event['reservation_label']
        require(sha(call_id) and call_id not in call_ids, 'unique call identity required')
        require(label in ledger and label not in labels, 'one existing reservation per call required')
        bound = ledger[label]
        require(bound['generation_bound'] <= min(4096, 4096-generation) and bound['prompt_bound'] + bound['generation_bound'] <= 8192, 'reservation exceeds episode/context bounds')
        require(event['request_sha256'] == digest(history), 'actual request history mismatch')
        call_ids.append(call_id); labels.append(label)
        status = event['status']
        if status in ('provider_error', 'timeout'):
            require(set(event) == {'kind','call_id_sha256','reservation_label','request_sha256','status'}, 'failed-call envelope must not claim completion/native data')
            category, detail = 'provider', status
            continue
        require(status == 'returned', 'known provider status required')
        response = event['response']
        rid = response['response_id_sha256']
        require(sha(rid) and rid not in reply_ids, 'unique returned response identity required')
        reply_ids.append(rid)
        usage = response['usage']
        require(integer(usage['prompt_tokens'], 1) and integer(usage['completion_tokens']), 'actual usage required')
        require(usage['prompt_tokens'] <= bound['prompt_bound'] and usage['completion_tokens'] <= bound['generation_bound'], 'actual usage exceeds reservation')
        generation += usage['completion_tokens']
        require(generation <= 4096, 'episode generation budget exceeded')
        finish = response['finish_reason']
        if finish != 'stop':
            require('native' not in event and 'native_error' not in event, 'non-stop reply cannot execute')
            category, detail = ('truncation', 'length') if finish == 'length' else ('provider', 'finish_reason:'+str(finish))
            continue
        try:
            action = action_from_reply(response['content'], schema)
        except ValueError:
            require('native' not in event and 'native_error' not in event, 'invalid action cannot execute')
            category, detail = 'format', 'invalid_action'
            continue
        if 'native_error' in event:
            require('native' not in event and event['native_error'] in ('transport', 'verifier', 'tool_timeout'), 'typed unscored native error required')
            category, detail = 'execution', event['native_error']
            continue
        native = event['native']
        obs = inspect_transport(native)
        actions.append(action); transports.append(native)
        history += [{'role':'assistant','content':response['content']}, {'role':'user','content':json.dumps(native, sort_keys=True, separators=(',', ':'))}]
        if native['done']:
            terminal_reward = native['reward']
            # On action32 the native environment auto-grades; this is a limit
            # stop, unless the model explicitly chose evaluate on that action.
            if len(actions) == 32 and action['action_type'] != 'evaluate':
                category, detail = 'budget', 'actions'
            elif obs['error'] == 'timed out':
                category, detail = 'execution', 'tool_timeout'
            else:
                category, detail, semantic = ('full' if terminal_reward == 1 else 'wrong'), 'native_terminal', terminal_reward
        elif obs['error'] == 'timed out':
            category, detail = 'execution', 'tool_timeout'
    require(category is not None, 'incomplete trajectory: explicit stop required')
    # Failures still replay the successfully executed prefix. Runtime errors
    # are unscored and not rerun blindly; the failing call itself is not replayed.
    fresh = replay(episode['task_id'], episode['seed'], actions)
    require(fresh['image'] == IMAGE and fresh['runtime_source'] == RUNTIME and fresh['uid_shell'] is True, 'trusted native replay identity required')
    require(fresh['reset_transport'] == reset and fresh['workspace'] == workspace, 'fresh replay input mismatch')
    require(fresh['transports'] == transports, 'fresh replay observations/reward mismatch')
    return {'phase':phase,'task_id':episode['task_id'],'seed':episode['seed'],'sample':episode['sample'],
            'family':group['family'],'case_sha256':group['case_sha256'],'workspace_sha256':group['workspace_sha256'],
            'category':category,'detail':detail,'semantic_reward':semantic,'terminal_reward_observed':terminal_reward,
            'calls':len(call_ids),'actions_replayed':len(actions),'generation_tokens':generation,
            'call_ids':call_ids,'response_ids':reply_ids,'reservation_labels':labels,
            'raw_sha256':digest(episode),'provider_authenticated':False,'reservation_chronology_attested':False,
            'is_training':False}


def assess_phase(rows, plan, phase):
    require(digest(plan) == PLAN_BODY_SHA256, 'unchanged native-derived protocol required')
    expected = {(r['task_id'],r['seed'],s) for r in plan['phases'][phase]['groups'] for s in range(4)}
    require(len(rows) == len(expected), 'complete phase denominator required')
    seen, calls, responses, labels = set(), set(), set(), set()
    for row in rows:
        key = row['task_id'], row['seed'], row['sample']
        require(row['phase'] == phase and key in expected and key not in seen, 'unique planned phase records required')
        seen.add(key)
        for field, identities in [('call_ids',calls),('response_ids',responses),('reservation_labels',labels)]:
            require(not identities.intersection(row[field]), 'cross-episode call/response/reservation reuse')
            identities.update(row[field])
        group = next(g for g in plan['phases'][phase]['groups'] if (g['task_id'],g['seed']) == key[:2])
        require(all(row[k] == group[k] for k in ('family','case_sha256','workspace_sha256')), 'normalized case mismatch')
        require(row['category'] in ('full','wrong')+FAILURES, 'known classification required')
        require(row['semantic_reward'] == (1 if row['category']=='full' else 0 if row['category']=='wrong' else None), 'semantic classification mismatch')
    counts = Counter(r['category'] for r in rows)
    groups=[]
    for g in plan['phases'][phase]['groups']:
        sample=[r for r in rows if (r['task_id'],r['seed']) == (g['task_id'],g['seed'])]
        valid=[r['semantic_reward'] for r in sample if r['category'] in ('full','wrong')]
        groups.append({'task_id':g['task_id'],'seed':g['seed'],'family':g['family'],
                       'full':sum(v==1 for v in valid),'wrong':sum(v==0 for v in valid),'failures':4-len(valid),
                       'productive':set(valid)=={0,1}})
    valid_count=counts['full']+counts['wrong']
    return {'phase':phase,'attempts':len(rows),'counts':dict(counts),'groups':groups,
            'full_fraction_all_attempts':counts['full']/len(rows),
            'full_fraction_valid':counts['full']/valid_count if valid_count else None,
            'productive_groups':sum(g['productive'] for g in groups),'new_training':False,'promotion':False}


def confirm(screen, confirmation, plan):
    a,b=assess_phase(screen,plan,'screen'),assess_phase(confirmation,plan,'confirmation')
    for field in ('case_sha256','workspace_sha256'):
        require(not {r[field] for r in screen}.intersection(r[field] for r in confirmation), 'confirmation case leakage')
    for field in ('call_ids','response_ids','reservation_labels'):
        require(not {i for r in screen for i in r[field]}.intersection(i for r in confirmation for i in r[field]), 'confirmation observed identity reuse')
    cells=lambda report:{(g['task_id'],g['family']) for g in report['groups'] if g['productive']}
    expected={(g['task_id'],g['family']) for g in plan['phases']['screen']['groups']}
    return {'screen':a,'confirmation':b,'sampled_cells_productive_both':sorted(cells(a)&cells(b)),
            'all_sampled_cells_provisional_signal':cells(a)&cells(b)==expected,
            'instruction_prefixes_disjoint':plan['initial_prompts_disjoint'],
            'whole_task_readiness':False,'model_improvement_claim':False,'promotion':False}


def audit_phase(episodes, plan, schema, reservations, replay, phase):
    """Bind every raw episode before complete-phase assessment; no partial promotion."""
    rows = [audit_episode(e, plan, schema, reservations, replay) for e in episodes]
    report = assess_phase(rows, plan, phase)
    used = {label for r in rows for label in r['reservation_labels']}
    report['reservation_labels_without_observed_calls'] = sorted(r['label'] for r in reservations if r['label'] not in used)
    report['rows'] = rows
    report['reservation_refunds'] = False
    return report
