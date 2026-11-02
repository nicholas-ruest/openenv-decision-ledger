"""Shared known-prefix reconstruction; no provider, reservations or terminal credit."""
import copy,json

def verify_known_prefix(job,path,events,row,counter,seen,*,trial,sampling,canonical,digest):
    """Replay known prefixes without assigning an unobserved terminal reward."""
    calls=[e for e in events if e['event']=='calling']
    generated=observed=replayed=0;fault=None
    for turn,call in enumerate(calls):
        if trial.finished:raise ValueError("call after terminal outcome")
        limit=min(6000 if turn==0 else 8096,8192-generated-observed-96)
        if limit<=0 or counter.context(trial.messages)+limit+96>24576:raise ValueError('original pre-call budget exhausted')
        request=dict(copy.deepcopy(sampling),messages=copy.deepcopy(trial.messages),max_tokens=limit)
        original=json.loads((path/('request-'+str(turn)+'.json')).read_text())
        if request!=original or digest(original)!=call['request_sha256'] or call['generation_limit']!=limit:raise ValueError('original failed-attempt request changed')
        response_path=path/('response-'+str(turn)+'.json')
        if not response_path.exists():break
        response=json.loads(response_path.read_text());identity=response.get('id');usage=response.get('usage',{})
        if not isinstance(identity,str) or not identity or identity in seen or any(type(usage.get(k)) is not int or usage[k]<0 for k in ('prompt_tokens','completion_tokens')):raise ValueError('original unique known reply and usage required')
        seen.add(identity)
        if usage['completion_tokens']>limit or usage['prompt_tokens']>28672 or usage['prompt_tokens']+usage['completion_tokens']>24576:
            fault='actual_token_overrun';break
        choices=response.get('choices')
        if not isinstance(choices,list) or len(choices)!=1 or choices[0].get('message',{}).get('role')!='assistant' or choices[0].get('message',{}).get('tool_calls') or choices[0].get('message',{}).get('function_call'):
            fault='provider_message_invalid';break
        generated+=usage['completion_tokens']
        try:result=trial.consume(response['choices'][0]['message'],response['choices'][0].get('finish_reason'))
        except Exception:
            fault='native_processing_unverified';break
        new_tokens=sum(counter.count(canonical(x)) for x in result['new_observations']);observed+=new_tokens;replayed+=1
        if generated+observed>8192 or counter.context(trial.messages)>24576 or usage['prompt_tokens']+usage['completion_tokens']+new_tokens>24576:
            fault='actual_observation_overrun';break
    expected={'native_processing_unverified':'execution','provider_message_invalid':'provider','actual_token_overrun':'budget','actual_observation_overrun':'budget'}
    if fault and row['category'] is not None and row['category']!=expected[fault]:raise ValueError('original failure does not match replayed prefix')
    return dict(known_prefix_responses_replayed=replayed,prefix_fault=fault,prefix_replay_is_not_terminal_evidence=True)
