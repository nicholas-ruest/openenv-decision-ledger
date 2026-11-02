"""Source/case-bound raw Native reconstruction, never provider or spend attestation."""
import json,importlib.util
from pathlib import Path
import case_binding as binding
if Path(binding.__file__).resolve()!=Path(__file__).with_name('case_binding.py').resolve():raise ValueError('exact sibling Native binding required')


def reconstruct(job,responses,counter,args):
    trial=binding.materialize(job,args) # Original immutable gate precedes Native trial.
    runtime=binding._runtime()
    value=runtime.p._observe(job,responses,counter,trial,True,dict(
        case_audit_sha256=trial.case_audit_sha256,source=args.expected_source))
    # A successful reconstruction says nothing about where the saved replies came from.
    value.pop('scripted');value.pop('live_evidence')
    value.update(kind='case_bound_native_reconstruction',replay_only=True,
        provider_provenance_attested=False,execution_authorized=False,selection_passed=False)
    reviews=[json.loads(step['result']['new_observations'][0]['feedback']) for step in value['steps']
             if step['result']['category']=='awaiting_revision']
    present=bool(reviews and reviews[0].get('final_output_domain_reminder')==runtime.r.REMINDER)
    value['record'].update(final_domain_reminder_presented=present,
        final_domain_reminder_exposed=present and len(responses)==2)
    return value


def verify(trace,counter,args):
    if trace.get('kind')!='case_bound_native_reconstruction' or trace.get('replay_only') is not True:
        raise ValueError('raw reconstruction only; no provider provenance promotion')
    original=reconstruct(trace['job'],trace['responses'],counter,args)
    if original!=trace:raise ValueError('source, case, request, reply, Native result or accounting changed')
    return dict(job=trace['job'],verified=True,replay_only=True,provider_provenance_attested=False,
                **original['record'])


def verify_phase(traces,counter,args):
    case=binding.gate.require_case(args)
    if len(traces)!=8 or [binding.gate.digest(t['job']) for t in traces]!=[binding.gate.digest(j) for j in case['jobs']]:
        raise ValueError('all eight original ordered assignments required')
    identities=[r.get('id') for t in traces for r in t['responses']]
    if any(not isinstance(i,str) or not i for i in identities) or len(identities)!=len(set(identities)):
        raise ValueError('original unique reply identities required')
    rows=[verify(t,counter,args) for t in traces]
    if len({t['prompt_sha256'] for t in traces})!=1 or len({t['problem_sha256'] for t in traces})!=1:
        raise ValueError('identical original first prompt and matched Native problem required')
    if any(r['computed_relation_exposed'] or r['usable_relation_counterexample_exposed'] or
           (r['final_domain_reminder_presented'] and r['job']['arm']!='final_domain_reminder') for r in rows):
        raise ValueError('original treatment exposure changed')
    return dict(kind='case_bound_phase_reconstruction',assigned=8,all_assigned_in_denominator=True,
        rows=rows,replay_only=True,provider_provenance_attested=False,execution_authorized=False,
        selection_passed=False,model_improvement=False)


def reconstruct_failure_prefix(job,path,events,row,counter,args,seen):
    trial=binding.materialize(job,args)
    runtime=binding._runtime();path=Path(path)
    reserved=[(i,e) for i,e in enumerate(events) if e['event']=='reserved']
    calls=[(i,e) for i,e in enumerate(events) if e['event']=='calling']
    replies=[(i,e) for i,e in enumerate(events) if e['event']=='response_received']
    labels=[job['attempt_id']+':'+str(i) for i in range(len(reserved))]
    if (len(reserved)>2 or len(calls)>len(reserved) or len(replies)>len(calls)
        or [e['label'] for _,e in reserved]!=labels or [e['label'] for _,e in calls]!=labels[:len(calls)]
        or any(reserved[i][0]>=n for i,(n,_) in enumerate(calls))
        or any(calls[i][0]>=n for i,(n,_) in enumerate(replies))
        or (len(reserved)==2 and (not replies or replies[0][0]>=reserved[1][0]))):
        raise ValueError('original reserve/call/reply order required')
    if (binding.gate.digest(row['job'])!=binding.gate.digest(job) or row['reservations']!=labels or row['calls']!=labels[:len(calls)]
        or row['response_ids']!=[e['response_id'] for _,e in replies]
        or row['category'] not in ('provider','budget','execution')
        or type(row['unknown_usage']) is not bool or type(row['known_generation_tokens']) is not int
        or (not row['unknown_usage'] and type(row['generation_tokens']) is not int)
        or row.get('semantic_reward') is not None or row['unknown_usage']!=(len(replies)<len(calls))
        or (row['unknown_usage'] and row['generation_tokens'] is not None)):
        raise ValueError('unknown usage and original record must remain unrewarded')
    known=0
    if any((path/('response-'+str(turn)+'.json')).exists()!=(turn<len(replies)) for turn in range(len(calls))):
        raise ValueError('saved replies must match original received events')
    for turn,(_,event) in enumerate(replies):
        response=json.loads((path/('response-'+str(turn)+'.json')).read_text())
        if response.get('id')!=event['response_id']:raise ValueError('original known reply differs')
        usage=response.get('usage',{}).get('completion_tokens')
        if type(usage) is not int or usage<0:raise ValueError('actual known prefix usage required')
        known+=usage
    if known!=row['known_generation_tokens'] or (not row['unknown_usage'] and known!=row['generation_tokens']):raise ValueError('known prefix usage changed')
    # The same pure core is used by the existing scripted finite archive verifier.
    spec=importlib.util.spec_from_file_location('late_domain_bound_prefix',Path(__file__).with_name('prefix_replay.py'))
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    result=helper.verify_known_prefix(job,path,events,row,counter,seen,trial=trial,
        sampling=runtime.SAMPLING,canonical=runtime.p.d.canonical,digest=runtime.p.digest)
    return dict(result,case_audit_sha256=trial.case_audit_sha256,source=args.expected_source,
        known_generation_tokens=known,unknown_usage=row['unknown_usage'],
        total_generation_tokens=None if row['unknown_usage'] else known,
        reconstructed_terminal_reward=None,provider_provenance_attested=False,
        execution_authorized=False,selection_passed=False)
