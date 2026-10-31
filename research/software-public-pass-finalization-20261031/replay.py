"""Independently replay the complete computed-feedback screen before selection."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import finalization_protocol as protocol
Trial=protocol.Trial

def verify_chunk(frozen,rows,events,counter):
    if frozen!=protocol.bundle(frozen.get('chunk')):raise ValueError('exact original chunk required')
    assigned={j['attempt_id'] for j in frozen['screen_jobs']}
    if any(e.get('attempt_id') not in assigned for e in events):raise ValueError('unassigned event')
    if len(rows)!=2 or [r['attempt_id'] for r in rows]!=[j['attempt_id'] for j in frozen['screen_jobs']]:raise ValueError('complete assigned chunk required')
    ids=[];calls=[];max_context=0;max_completion=0
    for job,row in zip(frozen['screen_jobs'],rows):
        for key,value in job.items():
            if row[key]!=value:raise ValueError('assignment identity changed')
        bound=protocol.capture(job)
        if any(row[k]!=bound[k] for k in ('prompt_sha256','problem_sha256')):raise ValueError('prompt changed')
        emitted=[e for e in events if e['attempt_id']==job['attempt_id']]
        called=[e['call_id'] for e in emitted if e['event']=='calling']
        reserved=[e['label'] for e in emitted if e['event']=='reserved']
        replies=[e for e in emitted if e['event']=='response']
        if called!=row['call_ids'] or reserved!=row['reservation_labels'] or len(called)>2:raise ValueError('call or reservation changed')
        calls+=called
        if [e['turn'] for e in replies]!=list(range(len(replies))):raise ValueError('turn order differs')
        trial=Trial(job);generation=0;observations=0;context=0;identities=[];finish=None;category=None;semantic=None;reward=None;controller=[];expected_controller=[]
        for turn,event in enumerate(replies):
            reply=event['response'];usage=reply['usage'];identity=hashlib.sha256(reply['id'].encode()).hexdigest()
            if any(type(usage.get(k)) is not int or usage[k]<0 for k in ('prompt_tokens','completion_tokens')):raise ValueError('known nonnegative usage required')
            if trial.closed:raise ValueError('call after terminal')
            limit=min(6000 if turn==0 else 8096,8192-generation-observations-96)
            intent=next(e for e in emitted if e['event']=='intent' and e['turn']==turn)
            if intent['max_tokens']!=limit or usage['completion_tokens']>limit or usage['prompt_tokens']>28672:raise ValueError('request/usage budget changed')
            request=dict(protocol.sampling_for(job,turn),messages=trial.messages,max_tokens=limit)
            if intent['request_sha256']!=protocol.digest(request) or intent['messages_sha256']!=protocol.digest(trial.messages):raise ValueError('sent request binding changed')
            identities.append(identity);generation+=usage['completion_tokens'];context=max(context,usage['prompt_tokens']+usage['completion_tokens'])
            if not isinstance(reply.get('choices'),list) or len(reply['choices'])!=1:raise ValueError('one reply choice required')
            choice=reply['choices'][0]
            if choice['message'].get('tool_calls') or choice['message'].get('function_call'):raise ValueError('unexpected tool payload')
            finish=choice.get('finish_reason')
            if finish=='length':category='truncation';break
            if finish!='stop':category='provider';break
            value=trial.consume(choice['message'].get('content'))
            obs=sum(counter.count(protocol.canonical(x)) for x in value['new_observations'])
            controller=value['controller_actions']
            if controller:expected_controller.append(dict(event='controller_actions',attempt_id=job['attempt_id'],turn=turn,actions=controller,observations_sha256=protocol.digest(value['new_observations'])))
            observations+=obs;context=max(context,counter.context(trial.messages),usage['prompt_tokens']+usage['completion_tokens']+obs)
            category=value['category'];semantic=value.get('semantic_reward');reward=value['native_reward']
        if row['controller_actions']!=controller or [e for e in emitted if e['event']=='controller_actions']!=expected_controller:raise ValueError('controller provenance changed')
        if identities!=row['response_ids']:raise ValueError('response identities changed')
        if row['response_id']!=(hashlib.sha256(protocol.canonical(identities).encode()).hexdigest() if identities else None):raise ValueError('aggregate response identity changed')
        ids+=identities
        if row['category'] not in ['provider','budget']:
            if len(replies)!=len(called) or (category,semantic,reward,finish)!=(row['category'],row['semantic_reward'],row['terminal_reward_observed'],row['finish_reason']):raise ValueError('native replay changed')
            if (generation,observations,context)!=(row['generation_tokens'],row['observation_tokens'],row['max_context']):raise ValueError('actual cost changed')
            if generation+observations>8192 or context>24576:raise ValueError('native budget exceeded')
        elif row['generation_tokens'] is not None and generation!=row['generation_tokens']:raise ValueError('failure usage changed')
        max_context=max(max_context,context);max_completion=max(max_completion,generation+observations)
    if len(set(ids))!=len(ids) or len(set(calls))!=len(calls):raise ValueError('reused call or response identity')
    return dict(response_ids=ids,call_ids=calls,max_context=max_context,max_completion=max_completion)

