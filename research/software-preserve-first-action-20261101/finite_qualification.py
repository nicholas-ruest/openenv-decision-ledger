"""Finite reserve-before-call qualification; live backend explicitly refused."""
import json
import os
from pathlib import Path
import time
import matched_protocol as p


def write(path, value):
    with path.open('a') as stream:
        stream.write(p.native.canonical(value)+'\n');stream.flush();os.fsync(stream.fileno())


def run(backend, counter, output, deadline):
    if backend.scripted is not True:
        raise ValueError('live caller not admitted or enabled')
    output = Path(output)
    if output.exists() or deadline <= time.monotonic():
        raise ValueError('fresh archive and one original phase deadline required')
    # Conservative existing financial quote dimensions, never a cap amendment.
    backend.admit([28672]*8, 6000, deadline)
    output.mkdir(mode=0o700, parents=True)
    events = output/'events.jsonl';records = output/'records.jsonl'
    rows = [];traces = [];stop = False
    for job in p.jobs('qualification'):
        if stop: break
        attempt = min(deadline, time.monotonic()+600)
        row = dict(job=job, category='budget', reservations=[], calls=[],
                   response_ids=[], unknown_usage=False, generation_tokens=0)
        stage = 'native_initialization';called = known = False
        try:
            trial = p.native.QualificationTrial(p.native.qualification_job(job['arm']))
            payload = dict(p.native.SAMPLING, messages=trial.messages, max_tokens=6000)
            if time.monotonic() >= attempt or counter.context(trial.messages)+6000+96 > 24576:
                stop = True
            else:
                label = job['attempt_id']+':0';stage = 'reservation'
                backend.reserve(label, 28672, 6000, attempt)
                row['reservations'].append(label)
                write(events, dict(event='reserved', label=label, attempt_id=job['attempt_id']))
                if time.monotonic() >= attempt:
                    stop = True
                else:
                    stage = 'provider';called = True;row['calls'].append(label)
                    write(events, dict(event='calling', label=label, attempt_id=job['attempt_id'],
                                      request_sha256=p.native.digest(payload), requested_max_tokens=6000))
                    response = backend.call(payload, min(360, attempt-time.monotonic()), job)
                    stage = 'response_validation';backend.check_reply(response)
                    usage = response.get('usage', {})
                    identity = response.get('id')
                    if (not isinstance(identity, str) or not identity
                        or identity in [i for r in rows for i in r['response_ids']]
                        or any(type(usage.get(k)) is not int or usage[k] < 0
                               for k in ('prompt_tokens', 'completion_tokens'))):
                        raise ValueError('unique response and known usage required')
                    known = True;row['response_ids'].append(identity)
                    row['generation_tokens'] = usage['completion_tokens']
                    write(events, dict(event='response', attempt_id=job['attempt_id'], response=response))
                    backend.check_message(response['choices'][0]['message'])
                    stage = 'accounting'
                    if (usage['completion_tokens'] > 6000 or usage['prompt_tokens'] > 28672
                        or usage['prompt_tokens']+usage['completion_tokens'] > 24576):
                        raise ValueError('actual generation/context budget exceeded')
                    if time.monotonic() >= attempt:
                        stop = True
                    else:
                        stage = 'native_replay'
                        trace = p.observe_scripted(job, response, counter)
                        verified = p.verify(trace, counter)
                        row.update(verified)
                        if time.monotonic() >= attempt:
                            row['category'] = 'budget';stop = True
                        elif row['category'] in ('provider', 'budget', 'execution'):
                            stop = True
                        else:
                            traces.append(trace)
                            with (output/(job['attempt_id']+'.trace.json')).open('x') as stream:
                                json.dump(trace, stream, indent=2)
        except Exception as exc:
            row['unknown_usage'] = called and not known
            if row['unknown_usage']: row['generation_tokens'] = None
            row['category'] = ('budget' if stage in ('reservation','accounting') else
                               'provider' if stage in ('provider','response_validation') else 'execution')
            stop = True
            write(events, dict(event='failure', stage=stage, error_type=type(exc).__name__,
                              attempt_id=job['attempt_id'], unknown_usage=row['unknown_usage']))
        write(records, row);rows.append(row)
    complete = len(traces)==8 and not stop and time.monotonic()<deadline
    if complete:
        report = p.verify_phase(traces, counter)
        with (output/'qualification-evidence.json').open('x') as stream: json.dump(report, stream, indent=2)
    summary = dict(scripted=True, live_evidence=False, assigned=8, recorded=len(rows),
        uncalled_assignments=8-len(rows), observed_calls=sum(len(r['calls']) for r in rows),
        unknown_usage_calls=sum(r['unknown_usage'] for r in rows), complete=complete,
        selection_passed=False, retries=0, stopped_on_failure=stop)
    with (output/'complete.json').open('x') as stream: json.dump(summary, stream, indent=2)
    return rows, summary
