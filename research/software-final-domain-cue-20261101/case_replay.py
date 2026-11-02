"""Source/case-bound raw Native reconstruction, never provider or spend attestation."""
import json
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
