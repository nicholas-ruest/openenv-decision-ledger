"""Read-only assembly of original finite qualification archives, including failure.

Never infers semantic outcomes for uncalled/unfinished attempts; no live gate.
"""
import json
from pathlib import Path
import matched_protocol as p


def lines(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x] if path.exists() else []


def assemble(output,counter):
    output=Path(output);assigned=p.jobs('qualification')
    records=lines(output/'records.jsonl');events=lines(output/'events.jsonl')
    if len(records)>8 or [r['job'] for r in records]!=assigned[:len(records)]:
        raise ValueError('original ordered assignment prefix required')
    rows=[];response_ids=set();traces=[]
    for index,job in enumerate(assigned):
        attempt=job['attempt_id'];ev=[e for e in events if e.get('attempt_id')==attempt]
        reserved=[e['label'] for e in ev if e['event']=='reserved']
        called=[e['label'] for e in ev if e['event']=='calling']
        replies=[e['response'] for e in ev if e['event']=='response']
        if (reserved not in ([],[attempt+':0']) or called not in ([],reserved)
            or len(replies)>len(called)):
            raise ValueError('reserve-before-call and one original response required')
        for response in replies:
            identity=response.get('id')
            if not isinstance(identity,str) or not identity or identity in response_ids:
                raise ValueError('unique actual response identity required')
            response_ids.add(identity)
        record=records[index] if index<len(records) else None
        trace_path=output/(attempt+'.trace.json')
        if record is None:
            if trace_path.exists():raise ValueError('trace has no original terminal record')
            rows.append(dict(job=job,recorded=False,category=None,observed_calls=len(called),unknown_usage=bool(called and not replies)))
            continue
        if record['reservations']!=reserved or record['calls']!=called:
            raise ValueError('durable request/reservation identity changed')
        if trace_path.exists():
            trace=json.loads(trace_path.read_text());verified=p.verify(trace,counter)
            if trace['job']!=job or replies!=[trace['response']]:raise ValueError('original reply/assignment differs')
            call=next(e for e in ev if e['event']=='calling')
            if call['request_sha256']!=trace['request_sha256'] or call['requested_max_tokens']!=6000:
                raise ValueError('original request binding differs')
            if any(record.get(k)!=v for k,v in verified.items()):raise ValueError('raw record differs from independent replay')
            traces.append(trace);rows.append(dict(verified,recorded=True,observed_calls=1,unknown_usage=False))
        else:
            if record['category'] not in ('provider','budget','execution'):
                raise ValueError('unreplayed record cannot become a semantic outcome')
            if record['unknown_usage'] and (not called or record['generation_tokens'] is not None):
                raise ValueError('unknown usage must retain original call without invented cost')
            rows.append(dict(job=job,recorded=True,category=record['category'],observed_calls=len(called),unknown_usage=record['unknown_usage']))
    if any(e.get('attempt_id') not in {j['attempt_id'] for j in assigned} for e in events):
        raise ValueError('undeclared original assignment event')
    summary_path=output/'complete.json'
    summary=json.loads(summary_path.read_text()) if summary_path.exists() else None
    complete=len(traces)==8 and summary is not None and summary.get('complete') is True
    if summary and (summary.get('scripted') is not True or summary.get('live_evidence') is not False
        or summary.get('recorded')!=len(records) or summary.get('observed_calls')!=sum(r['observed_calls'] for r in rows)):
        raise ValueError('original scripted phase summary differs')
    evidence=p.verify_phase(traces,counter) if complete else None
    return dict(kind='preserve_first_qualification_archive',scripted=True,live_evidence=False,
        assigned=8,recorded=len(records),independently_replayed=len(traces),rows=rows,
        complete=complete,fitness_eligible=complete,selection_passed=False,evidence=evidence)
