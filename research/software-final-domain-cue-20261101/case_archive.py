"""Read-only case-bound phase reconstruction. Never attests a provider or admits work."""
import json
from pathlib import Path
import case_replay as replay
if Path(replay.__file__).resolve()!=Path(__file__).with_name('case_replay.py').resolve():
    raise ValueError('exact sibling replay required')


def read(path):
    return json.loads(path.read_text())


def assemble(output,counter,args):
    # Admission refusal must precede archive I/O and Native initialization.
    case=replay.binding.gate.require_case(args)
    output=Path(output);jobs=case['jobs'];digest=replay.binding.gate.digest
    if len(jobs)!=8 or digest(read(output/'assignments.json'))!=digest(jobs):
        raise ValueError('all eight original ordered assignments required')
    seen=set();all_ids=set();rows=[];traces=[]
    for job in jobs:
        identity=job['attempt_id']
        if len(identity)!=64 or any(c not in '0123456789abcdef' for c in identity):
            raise ValueError('sealed assignment identity required')
        path=output/identity
        events=[json.loads(x) for x in (path/'events.jsonl').read_text().splitlines()] if (path/'events.jsonl').exists() else []
        if any(e.get('event') not in ('reserved','calling','response_received','failure') for e in events):
            raise ValueError('unknown archive event')
        reserved=[(i,e) for i,e in enumerate(events) if e['event']=='reserved']
        calls=[(i,e) for i,e in enumerate(events) if e['event']=='calling']
        replies=[(i,e) for i,e in enumerate(events) if e['event']=='response_received']
        labels=[identity+':'+str(i) for i in range(len(reserved))]
        if (len(reserved)>2 or len(calls)>len(reserved) or len(replies)>len(calls)
            or [e['label'] for _,e in reserved]!=labels
            or [e['label'] for _,e in calls]!=labels[:len(calls)]
            or any(reserved[i][0]>=n for i,(n,_) in enumerate(calls))
            or any(calls[i][0]>=n for i,(n,_) in enumerate(replies))
            or (len(reserved)==2 and (not replies or replies[0][0]>=reserved[1][0]))):
            raise ValueError('original reserve/call/reply sequence required')
        # Stray files cannot invent known outcomes, calls or observations.
        for turn in (0,1):
            if ((path/('request-'+str(turn)+'.json')).exists()!=(turn<len(calls))
                or (path/('response-'+str(turn)+'.json')).exists()!=(turn<len(replies))):
                raise ValueError('saved files differ from observed calls/replies')
        responses=[read(path/('response-'+str(i)+'.json')) for i in range(len(replies))]
        known=0
        for response,(_,event) in zip(responses,replies):
            tokens=response.get('usage',{}).get('completion_tokens')
            reply_id=response.get('id')
            if not isinstance(reply_id,str) or not reply_id or reply_id in all_ids:
                raise ValueError('original unique reply identities required')
            all_ids.add(reply_id)
            if type(tokens) is not int or tokens<0 or reply_id!=event['response_id']:
                raise ValueError('known usage or reply identity changed')
            known+=tokens
        recorded=(path/'record.json').exists()
        unknown=len(replies)<len(calls)
        row=read(path/'record.json') if recorded else dict(job=job,category='budget',
            failure_origin='missing_original_record',semantic_reward=None,
            reservations=labels,calls=labels[:len(calls)],response_ids=[e['response_id'] for _,e in replies],
            unknown_usage=unknown,known_generation_tokens=known,generation_tokens=None if unknown else known)
        if (digest(row['job'])!=digest(job) or row['reservations']!=labels
            or row['calls']!=labels[:len(calls)] or row['response_ids']!=[e['response_id'] for _,e in replies]
            or type(row['unknown_usage']) is not bool or row['unknown_usage']!=unknown
            or type(row['known_generation_tokens']) is not int or row['known_generation_tokens']!=known
            or (unknown and row['generation_tokens'] is not None)
            or (not unknown and (type(row['generation_tokens']) is not int or row['generation_tokens']!=known))):
            raise ValueError('original accounting record changed')
        if (path/'trace.json').exists():
            if not recorded or unknown:raise ValueError('terminal trace requires original known record')
            trace=read(path/'trace.json');verified=replay.verify(trace,counter,args)
            if (digest(trace['job'])!=digest(job) or trace['responses']!=responses
                or any(row.get(k)!=v for k,v in trace['record'].items())
                or len(trace['requests'])!=len(calls)):
                raise ValueError('terminal trace differs from original attempt')
            for turn,(request,response) in enumerate(zip(trace['requests'],responses)):
                call=calls[turn][1]
                if (read(path/('request-'+str(turn)+'.json'))!=request
                    or call['request_sha256']!=digest(request) or call['generation_limit']!=request['max_tokens']
                    or response['id'] in seen):raise ValueError('original request or unique reply differs')
                seen.add(response['id'])
            rows.append(dict(verified,recorded=True));traces.append(trace)
        else:
            prefix=replay.reconstruct_failure_prefix(job,path,events,row,counter,args,seen)
            partial=dict(row,**prefix,recorded=recorded)
            # A raw interrupted record cannot contribute an unreplayed terminal reward.
            partial['terminal_reward_observed']=None
            rows.append(partial)
    complete=len(traces)==8
    phase=replay.verify_phase(traces,counter,args) if complete else None
    return dict(kind='case_bound_archive_reconstruction',assigned=8,rows=rows,
        all_assigned_in_denominator=True,independently_replayed_terminal_attempts=len(traces),
        all_terminal_attempts_reconstructed=complete,phase_reconstruction=phase,
        case_audit_sha256=case['case_audit_sha256'],source=args.expected_source,
        replay_only=True,provider_provenance_attested=False,execution_authorized=False,
        selection_passed=False,model_improvement=False)
