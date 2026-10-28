"""Durable multi-action media phase core; no provider implementation or paid CLI.

External admission/accounting, bounded provider/native adapters and process-group
supervision are mandatory dependencies. Clock checks alone cannot interrupt a
blocked callback or establish a provider billing stop.
"""
import copy
import json
import math
import os
from pathlib import Path

from durable_phase import durable_new
from media_protocol import digest, messages, SAMPLING
from trajectory_audit import (audit_episode, assess_phase, action_from_reply,
                              require, PLAN_BODY_SHA256)


def deadline_check(deadline, now):
    current=now()
    require(type(current) in (int,float) and math.isfinite(current) and current < deadline, 'wall deadline reached')


def schedule(plan, phase):
    require(digest(plan)==PLAN_BODY_SHA256 and phase in plan['phases'], 'frozen phase required')
    # Interleave cases within each sample to avoid exhausting one family first.
    return [(g['task_id'],g['seed'],sample) for sample in range(4) for g in plan['phases'][phase]['groups']]


def run_phase(root, plan, schema, phase, prefix, deadline, admitted, now,
              open_env, reserve, reservations, dispatch, replay, *, accounting_factory, accounting_config):
    """One fresh 16-attempt phase. Callbacks are offline doubles in tests.

    open_env(task,seed) returns {reset_record, step, close}; reset_record carries
    native reset/workspace/runtime/UID fields. reserve(label,history,remaining)
    must durably reserve within the EXISTING whole-phase allocation before return.
    dispatch(history,label,deadline) returns the auditor's raw call envelope;
    this core binds its label/request to the already persisted intent.
    """
    require(admitted is True, 'external whole-phase admission required')
    require(type(deadline) in (int,float) and math.isfinite(deadline), 'finite deadline required')
    start=now();require(type(start) in (int,float) and math.isfinite(start) and 0 < deadline-start <= 1800, 'deadline within1800seconds required')
    from accounting_archive import validate_config, bind_budget
    validate_config(accounting_config)
    jobs=schedule(plan,phase)
    require(isinstance(prefix,str) and 1<=len(prefix)<=80 and all(c.isalnum() or c in '-_' for c in prefix), 'explicit safe archive namespace required')
    root=Path(root);root.mkdir(mode=0o700,exist_ok=False)
    fd=os.open(root.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
    durable_new(root,'accounting.json',accounting_config)
    durable_new(root,'claim.json',{'phase':phase,'jobs':jobs,'plan_sha256':digest(plan),'prefix':prefix,'resume_authorized':False,'accounting_mode':'local_pinned_generation_plus_observation','accounting_sha256':digest(accounting_config)})
    rows=[];seen_calls=set();seen_responses=set();seen_labels=set()
    try:
        for seq,(task,seed,sample) in enumerate(jobs):
            deadline_check(deadline,now)
            env=open_env(task,seed)
            try:
                episode=copy.deepcopy(env['reset_record'])
                episode.update(phase=phase,task_id=task,seed=seed,sample=sample,
                               sampling_sha256=plan['sampling_sha256'],events=[])
                # Validate the actual input before any reservation or dispatch.
                preview={**episode,'events':[{'kind':'budget','reason':'deadline'}]}
                audit_episode(preview,plan,schema,reservations(),replay)
                episode['accounting_sha256']=digest(accounting_config)
                history=messages(episode['reset_transport'],schema)
                accounting=accounting_factory(history)
                bind_budget(accounting,accounting_config)
                durable_new(root,f'{seq:02d}-reset.json',episode)
                generated=0
                for action_index in range(32):
                    deadline_check(deadline,now)
                    allowance=accounting.allowance(history)
                    if allowance<1:
                        reason='context' if accounting.context_used>=accounting.context else 'generation'
                        episode['events'].append({'kind':'budget','reason':reason})
                        break
                    label=f'{prefix}:{seq}:{action_index}'
                    reserve(label,copy.deepcopy(history),allowance)
                    # Reservation may block or consume the remaining wall time.
                    deadline_check(deadline,now)
                    ledger=reservations();matches=[r for r in ledger if r['label']==label]
                    require(len(matches)==1,'exact existing reservation required before dispatch')
                    b=matches[0]
                    require(type(b['prompt_bound']) is int and b['prompt_bound']>=accounting.context_used and b['prompt_bound']>0 and type(b['generation_bound']) is int and 0<b['generation_bound']<=allowance and b['prompt_bound']+b['generation_bound']<=8192,'bounded measured-context reservation required before dispatch')
                    audit_episode({**episode,'events':episode['events']+[{'kind':'budget','reason':'actions'}]},plan,schema,ledger,replay)
                    deadline_check(deadline,now)
                    stem=f'{seq:02d}-{action_index:02d}'
                    durable_new(root,stem+'-intent.json',{'label':label,'request_sha256':digest(history),'reservation':b,'accounting_sha256':digest(accounting_config)})
                    result=dispatch(copy.deepcopy(history),label,deadline)
                    # Save returned raw data BEFORE parsing or executing shell text.
                    durable_new(root,stem+'-provider.json',{'payload':result,'sha256':digest(result)})
                    deadline_check(deadline,now)
                    require(result['reservation_label']==label and result['request_sha256']==digest(history),'provider envelope/intent mismatch')
                    require('native' not in result and 'native_error' not in result,'native result must come from local adapter')
                    event=copy.deepcopy(result)
                    terminal=False
                    if event['status']=='returned':
                        accounting.reply(event['response']['usage']['completion_tokens'])
                    if event['status']=='returned' and event['response']['finish_reason']=='stop':
                        try:action=action_from_reply(event['response']['content'],schema)
                        except ValueError:action=None
                        if action is not None:
                            try:event['native']=env['step'](action,deadline)
                            except Exception as exc:
                                durable_new(root,stem+'-native-error.json',{'exception_type':type(exc).__name__})
                                event['native_error']='transport'
                    durable_new(root,stem+'-event.json',{'payload':event,'sha256':digest(event)})
                    episode['events'].append(event)
                    next_history=copy.deepcopy(history)
                    if 'response' in event:
                        next_history.append({'role':'assistant','content':event['response']['content']})
                        accounting.context_used=accounting.counter.context(next_history)
                    if 'native' in event:
                        next_history.append({'role':'user','content':json.dumps(event['native'],sort_keys=True,separators=(',',':'))})
                        accounting.observation(event['native'],next_history)
                    deadline_check(deadline,now)
                    # An explicit budget stop makes a still-open prefix auditable.
                    if 'native' in event and event['native'].get('done') is False and event['native']['observation'].get('error')!='timed out':
                        preview={**episode,'events':episode['events']+[{'kind':'budget','reason':'actions'}]}
                    else:preview=episode;terminal=True
                    validated=audit_episode(preview,plan,schema,reservations(),replay)
                    validated=accounting.project(validated)
                    if accounting.snapshot()['overflow_reason']:
                        terminal=True
                        if 'native' in event and not event['native']['done']:
                            episode['events'].append({'kind':'budget','reason':accounting.snapshot()['overflow_reason']})
                    for field,seen in [('call_ids',seen_calls),('response_ids',seen_responses),('reservation_labels',seen_labels)]:
                        # Prefix identities repeat legitimately within this episode.
                        require(not seen.intersection(validated[field]), 'observed identity reused across episodes')
                    durable_new(root,stem+'-validated.json',{'category':validated['category'],'raw_sha256':digest(preview)})
                    deadline_check(deadline,now)
                    if terminal:break
                    generated=validated['generation_tokens']
                    history=next_history
                row=audit_episode(episode,plan,schema,reservations(),replay)
                row=accounting.project(row)
                for field,seen in [('call_ids',seen_calls),('response_ids',seen_responses),('reservation_labels',seen_labels)]:seen.update(row[field])
                durable_new(root,f'{seq:02d}-episode.json',{'payload':episode,'sha256':digest(episode),'validated':row})
                rows.append(row)
            finally:
                env['close']()
        deadline_check(deadline,now)
        report=assess_phase(rows,plan,phase)
        report.update(complete=True,is_training=False,promotion=False)
        durable_new(root,'complete.json',report)
        return report
    except BaseException as exc:
        durable_new(root,'aborted.json',{'exception_type':type(exc).__name__,'saved_episodes':len(rows),'resume_authorized':False})
        raise


def inspect_saved(root):
    """Read-only integrity inspection; never resumes dispatch."""
    root=Path(root);claim=json.loads((root/'claim.json').read_text());count=0
    for pattern in ('*-provider.json','*-event.json','*-episode.json'):
        for path in root.glob(pattern):
            row=json.loads(path.read_text());require(digest(row['payload'])==row['sha256'],'archive checksum mismatch');count+=1
    return {'claim':claim,'saved_envelopes':count,'resume_authorized':False}
