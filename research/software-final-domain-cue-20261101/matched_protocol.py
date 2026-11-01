"""Exact qualification-only replay for the late reminder; no provider or live cases."""
import copy,importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('late_domain_native',HERE/'revision_environment.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
old=r.ROOT/'research/software-entry-order-review-20261101'
spec=importlib.util.spec_from_file_location('late_domain_original_replay',old/'matched_protocol.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
NAMESPACE='final-review-domain-reminder-20261101'
SAMPLING=copy.deepcopy(p.SAMPLING)

def jobs(phase='qualification'):
    if phase!='qualification':raise ValueError('live screen and confirmation cases remain unsealed')
    result=[]
    for sample in range(4):
        for arm in r.ARMS if sample%2==0 else reversed(r.ARMS):
            value=dict(namespace=NAMESPACE,phase=phase,task_id='software_repair-ignore-d3',seed=r.original.QUALIFICATION_SEED,sample=sample,arm=arm)
            result.append(dict(value,attempt_id=p.digest(value)))
    return result

class Trial(p.Trial):
    def __init__(self,job):
        if job not in jobs():raise ValueError('exact already-seen qualification assignment required')
        self._initialize(job,r.RevisionEnvironment(arm=job['arm']))

def observe(job,responses,counter):
    trial=Trial(job)
    trace=p._observe(job,responses,counter,trial,True,{})
    reviews=[json.loads(step['result']['new_observations'][0]['feedback']) for step in trace['steps'] if step['result']['category']=='awaiting_revision']
    present=bool(reviews and reviews[0].get('final_output_domain_reminder')==r.REMINDER)
    trace['record'].update(final_domain_reminder_presented=present,final_domain_reminder_exposed=present and len(responses)==2)
    return trace

def verify(trace,counter):
    if trace.get('scripted') is not True or trace.get('live_evidence') is not False:raise ValueError('qualification cannot become model evidence')
    reconstructed=observe(trace['job'],trace['responses'],counter)
    if trace!=reconstructed:raise ValueError('original request, reply, feedback, Native result or token accounting changed')
    return dict(job=trace['job'],verified=True,scripted=True,live_evidence=False,**reconstructed['record'])

def verify_phase(traces,counter):
    if len(traces)!=8 or [x['job'] for x in traces]!=jobs():raise ValueError('all eight original ordered assignments required')
    identities=[x['id'] for trace in traces for x in trace['responses']]
    if len(identities)!=len(set(identities)):raise ValueError('cross-attempt reply reuse')
    rows=[verify(t,counter) for t in traces]
    if len({t['prompt_sha256'] for t in traces})!=1 or len({t['problem_sha256'] for t in traces})!=1:raise ValueError('identical original first prompt and Native problem required')
    for row in rows:
        if row['computed_relation_exposed'] or row['usable_relation_counterexample_exposed']:raise ValueError('computed diagnostics must be withheld in both arms')
        if row['final_domain_reminder_presented'] and row['job']['arm']!='final_domain_reminder':raise ValueError('control received the treatment reminder')
    return dict(kind='final_domain_cue_qualification',scripted=True,live_evidence=False,assigned=8,all_assigned_in_denominator=True,rows=rows,selection_passed=False,model_improvement=False,is_training=False)
