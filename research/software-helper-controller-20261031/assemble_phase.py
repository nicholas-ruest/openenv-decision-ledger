"""Assemble eight assigned qualification outcomes; never admit live evidence."""
import json
from pathlib import Path
import matched_protocol as p
from replay_matched import verify


def assemble(chunks,counter):
    if len(chunks)!=4:raise ValueError('four ordered original chunk paths required')
    assigned=p.jobs('qualification');observed={};calls=set();responses=set();reservations=set()
    stopped=False;partial=False;verified=0
    for i,path in enumerate(map(Path,chunks)):
        if not path.exists():partial=True;stopped=True;continue
        if stopped:raise ValueError('later chunk after incomplete/stopped phase')
        done=json.loads((path/'complete.json').read_text())
        rows=[json.loads(l) for l in (path/'records.jsonl').read_text().splitlines()]
        events=[json.loads(l) for l in (path/'events.jsonl').read_text().splitlines()]
        jobs=[j for j in assigned if j['sample']==i]
        if (done.get('scripted') is not True or done.get('live_evidence') is not False
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
            if any(ids.count(x)!=1 or x not in labels for x in ids):raise ValueError('unreserved/duplicate call')
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
                proof=verify(trace,counter)
                for k in ['category','generation_tokens','native_observation_tokens','controller_observation_tokens','controller_actions']:
                    if row.get(k)!=proof[k]:raise ValueError('record differs from independent Native replay')
                observed[identity]=dict(job=job,recorded=True,replayed=True,**proof);verified+=1
            else:
                # Failure rows remain descriptive. No invented fitness cost or
                # claim that an absent Native trace was independently replayed.
                if not done['stopped_on_failure'] or row['category'] not in ('provider','budget','execution'):
                    raise ValueError('missing independent trace for a completed outcome')
                observed[identity]=dict(job=job,recorded=True,replayed=False,category=row['category'],
                    generation_tokens=row['generation_tokens'],unknown_usage=unknown,semantic_reward=None,
                    controller_actions=row.get('controller_actions',[]))
        if phase_calls!=done['observed_calls'] or sum(r['unknown_usage'] for r in rows)!=done['unknown_usage_calls']:
            raise ValueError('phase call/usage totals differ')
        stopped=done['stopped_on_failure'];partial|=stopped or len(rows)<2
    rows=[observed.get(j['attempt_id'],dict(job=j,recorded=False,replayed=False,category='unexecuted',
          generation_tokens=None,semantic_reward=None,controller_actions=[])) for j in assigned]
    return dict(kind='qualification_phase_assembly',scripted=True,live_evidence=False,
        assigned_jobs=assigned,rows=rows,assigned=8,recorded=sum(r['recorded'] for r in rows),
        independently_replayed=verified,unexecuted=sum(not r['recorded'] for r in rows),
        actual_scripted_calls=len(calls),known_scripted_replies=len(responses),
        complete=not partial and verified==8,all_assigned_in_denominator=True,
        new_model_calls=0,model_improvement=False,leaderboard_gain=False,promotion=False)
