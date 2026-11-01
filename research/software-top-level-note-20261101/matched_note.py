"""Frozen matched qualification using the existing one-action replay engine."""
import copy
import top_level_note as n

base=n.original.load('top_level_existing_replay',
    'research/software-preserve-first-action-20261101/matched_protocol.py')
SEEDS=dict(qualification=n.original.QUALIFICATION_SEED,screen=3200000,confirmation=3210000)


def jobs(phase):
    if phase not in SEEDS:raise ValueError('explicit original phase required')
    rows=[]
    for sample in range(4):
        for arm in n.ARMS if sample%2==0 else reversed(n.ARMS):
            value=dict(namespace='top-level-note-20261101',phase=phase,task_id=n.original.TASK,
                       seed=SEEDS[phase],sample=sample,arm=arm)
            rows.append(dict(value,attempt_id=n.original.digest(value)))
    return rows


def observe(job,response,counter):
    if job not in jobs('qualification'):raise ValueError('already-seen qualification only')
    trial=n.QualificationTrial(n.job(job['arm']))
    trace=base._observe(job,response,counter,trial,True,{})
    trace['record']['failure_origin']=trial.last_outcome['failure_origin']
    # Native category and reward stay unchanged. No failure becomes reasoning.
    trace['record']['native_compile_rejected']=trial.last_outcome.get('compile_rejected') is True
    trace['record']['native_runtime_error_observed']=trial.last_outcome.get('hidden_execution_errors',0)>0
    return trace


def verify(trace,counter):
    if trace.get('scripted') is not True or trace.get('live_evidence') is not False:
        raise ValueError('scripted qualification cannot become live evidence')
    replay=observe(trace['job'],trace['response'],counter)
    if replay!=trace:raise ValueError('original request, Native outcome or failure origin differs')
    return dict(job=trace['job'],verified=True,scripted=True,live_evidence=False,**replay['record'])


def verify_phase(traces,counter):
    if len(traces)!=8 or [x['job'] for x in traces]!=jobs('qualification'):
        raise ValueError('all original ordered assignments required')
    identities=[x['response']['id'] for x in traces]
    if len(set(identities))!=8:raise ValueError('reused reply identity')
    rows=[verify(t,counter) for t in traces]
    if len({x['problem_sha256'] for x in traces})!=1:raise ValueError('matched original Native problem required')
    return dict(kind='top_level_note_qualification',scripted=True,live_evidence=False,
        assigned=8,all_assigned_in_denominator=True,rows=rows,selection_passed=False,
        model_improvement=False,is_training=False)


def plan():
    value=n.plan()
    value.update(screen_jobs=jobs('screen'),confirmation_jobs=jobs('confirmation'),
        live_continuation_policy_frozen=False,
        required_next_step='Freeze future caller handling of verified model-code failures separately from provider/Native infrastructure failures, retaining zero reward and full denominator; no live caller/admission is supplied here.')
    return copy.deepcopy(value)
