"""Independent eight-assignment qualification and sealed-screen archive replay."""
import json
from pathlib import Path
import failure_protocol as p
from failure_protocol import verify


def assemble(chunks,counter):
    if len(chunks)!=4:raise ValueError('four ordered original chunk paths required')
    return _assemble(chunks,counter,'qualification',verify,None)



def assemble_screen(chunks,counter,case_audit,case_sha256):
    from finite_qualification import require_live_ready
    from failure_protocol import verify_screen
    require_live_ready(case_audit,case_sha256)
    return _assemble(chunks,counter,'screen',lambda t,c:verify_screen(t,c,case_audit,case_sha256),case_sha256)


def _assemble(chunks,counter,phase,replay,case_sha256):
    if len(chunks)!=4:raise ValueError('four ordered original chunk paths required')
    scripted=phase=='qualification'
    assigned=p.jobs(phase);observed={};calls=set();responses=set();reservations=set()
    stopped=False;partial=False;verified=0
    for i,path in enumerate(map(Path,chunks)):
        if not path.exists():partial=True;stopped=True;continue
        if stopped:raise ValueError('later chunk after incomplete/stopped phase')
        done=json.loads((path/'complete.json').read_text())
        rows=[json.loads(l) for l in (path/'records.jsonl').read_text().splitlines()]
        events=[json.loads(l) for l in (path/'events.jsonl').read_text().splitlines()]
        jobs=[j for j in assigned if j['sample']==i]
        if (done.get('scripted') is not scripted or done.get('live_evidence') is not (not scripted)
                or (not scripted and (done.get('case_audit_sha256')!=case_sha256 or done.get('execution_sha256')!=__import__('failure_materializer').execution_hashes()))
                or done.get('assigned_attempts')!=2 or done.get('recorded_attempts')!=len(rows)
                or not 0<len(rows)<=2 or [r['job'] for r in rows]!=jobs[:len(rows)]
                or done.get('uncalled_assignments')!=2-len(rows)):
            raise ValueError('original assigned qualification records required')
        if any(e.get('attempt_id') not in {j['attempt_id'] for j in jobs} for e in events):
            raise ValueError('unassigned event')
        phase_calls=0
        for row in rows:
            job=row['job'];identity=job['attempt_id'];es=[e for e in events if e['attempt_id']==identity]
            labels=[e['label'] for e in es if e['event']=='reserved']
            ids=[e['label'] for e in es if e['event']=='calling']
            replies=[e['response'] for e in es if e['event']=='response']
            reply_ids=[r['id'] for r in replies]
            if labels!=row['reservations'] or ids!=row['calls'] or reply_ids!=row['response_ids']:
                raise ValueError('raw identities differ from recorded accounting')
            if (len(labels)>2 or labels!=[identity+':'+str(turn) for turn in range(len(labels))]
                    or ids!=labels[:len(ids)] or len(replies)>len(ids)):
                raise ValueError('original reserved/called turn identity required')
            for values,seen in [(labels,reservations),(ids,calls),(reply_ids,responses)]:
                if len(set(values))!=len(values) or set(values)&seen:raise ValueError('reused identity')
                seen.update(values)
            unknown=len(ids)!=len(replies)
            usage=[r.get('usage',{}).get('completion_tokens') for r in replies]
            if any(type(x) is not int or x<0 for x in usage):raise ValueError('invalid claimed known usage')
            if row['unknown_usage']!=unknown or row['generation_tokens']!=(None if unknown else sum(usage)):
                raise ValueError('unknown usage cannot become known or zero')
            phase_calls+=len(ids)
            trace_file=path/(identity+'.trace.json')
            if trace_file.exists():
                trace=json.loads(trace_file.read_text())
                if trace['job']!=job or [e['response'] for e in trace['events']]!=replies:
                    raise ValueError('trace/raw response identity differs')
                proof=replay(trace,counter)
                if not scripted:
                    actual=[{k:e[k] for k in ('request_sha256','prompt_sha256','requested_max_tokens')} for e in es if e['event']=='calling']
                    if actual!=trace['requests']:raise ValueError('raw request identity differs from independently replayed transcript')
                for k in ['category','generation_tokens','native_observation_tokens','advice_observation_tokens','advice_deliveries']:
                    if row.get(k)!=proof[k]:raise ValueError('record differs from independent Native replay')
                observed[identity]=dict(job=job,recorded=True,replayed=True,**proof);verified+=1
            else:
                # Failure rows remain descriptive. No invented fitness cost or
                # claim that an absent Native trace was independently replayed.
                if not done['stopped_on_failure'] or row['category'] not in ('provider','budget','execution'):
                    raise ValueError('missing independent trace for a completed outcome')
                observed[identity]=dict(job=job,recorded=True,replayed=False,category=row['category'],
                    generation_tokens=row['generation_tokens'],unknown_usage=unknown,semantic_reward=None,
                    advice_deliveries=row.get('advice_deliveries',0))
        if phase_calls!=done['observed_calls'] or sum(r['unknown_usage'] for r in rows)!=done['unknown_usage_calls']:
            raise ValueError('phase call/usage totals differ')
        stopped=done['stopped_on_failure'];partial|=stopped or len(rows)<2
    rows=[observed.get(j['attempt_id'],dict(job=j,recorded=False,replayed=False,category='unexecuted',
          generation_tokens=None,semantic_reward=None,advice_deliveries=0)) for j in assigned]
    result=dict(kind=phase+'_phase_assembly',scripted=scripted,live_evidence=not scripted,
        assigned_jobs=assigned,rows=rows,assigned=8,recorded=sum(r['recorded'] for r in rows),
        independently_replayed=verified,unexecuted=sum(not r['recorded'] for r in rows),
        actual_calls=len(calls),known_replies=len(responses),
        complete=not partial and verified==8,all_assigned_in_denominator=True,
        new_model_calls=0,model_improvement=False,leaderboard_gain=False,promotion=False)

    if scripted:result.update(actual_scripted_calls=len(calls),known_scripted_replies=len(responses))

    if not scripted:result.update(case_audit_sha256=case_sha256,execution_sha256=__import__('failure_materializer').execution_hashes(),new_model_calls=len(calls))
    return result
