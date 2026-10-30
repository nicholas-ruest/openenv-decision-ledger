"""Independently replay the complete computed-feedback screen before selection."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from caller import ROOT,modules,load
protocol,Trial=modules()

def verify_chunk(frozen,rows,events,counter):
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
        trial=Trial(job);generation=0;observations=0;context=0;identities=[];finish=None;category=None;semantic=None;reward=None
        for turn,event in enumerate(replies):
            reply=event['response'];usage=reply['usage'];identity=hashlib.sha256(reply['id'].encode()).hexdigest()
            if any(type(usage.get(k)) is not int or usage[k]<0 for k in ('prompt_tokens','completion_tokens')):raise ValueError('known nonnegative usage required')
            if trial.closed:raise ValueError('call after terminal')
            limit=min(6000 if turn==0 else 8096,8192-generation-observations-96)
            intent=next(e for e in emitted if e['event']=='intent' and e['turn']==turn)
            if intent['max_tokens']!=limit or usage['completion_tokens']>limit or usage['prompt_tokens']>28672:raise ValueError('request/usage budget changed')
            request=dict(frozen['sampling'],messages=trial.messages,max_tokens=limit)
            if intent['request_sha256']!=protocol.digest(request) or intent['messages_sha256']!=protocol.digest(trial.messages):raise ValueError('sent request binding changed')
            identities.append(identity);generation+=usage['completion_tokens'];context=max(context,usage['prompt_tokens']+usage['completion_tokens'])
            choice=reply['choices'][0];finish=choice.get('finish_reason')
            if finish=='length':category='truncation';break
            if finish!='stop':category='provider';break
            value=trial.consume(choice['message'].get('content'))
            obs=counter.count(protocol.canonical(trial.native[-1])) if trial.native and len(trial.native)==turn+1 else 0
            observations+=obs;context=max(context,counter.context(trial.messages),usage['prompt_tokens']+usage['completion_tokens']+obs)
            category=value['category'];semantic=value.get('semantic_reward');reward=value['native_reward']
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

def main():
    p=argparse.ArgumentParser();p.add_argument('--chunks',type=Path,nargs=4,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--tokenizer',type=Path,required=True);p.add_argument('--expected-source',required=True);a=p.parse_args()
    if subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()!=a.expected_source:raise ValueError('source differs')
    subprocess.run(['git','-C',str(ROOT),'diff','--quiet','HEAD'],check=True)
    helper=load('feedback_replay_counter',ROOT/'integrations/openenv-arena/scripts/calibrate.py')
    counter=helper.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=a.tokenizer,tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
    rows=[];ids=[];calls=[];ctx=0;completion=0
    for index,path in enumerate(a.chunks):
        if not (path/'complete.json').exists():
            with a.output.open('x') as f:json.dump(dict(status='inconclusive_incomplete_experiment',assigned=8,completed_chunks=index,all_assigned_jobs=protocol.schedule('screen'),selection_passed=False,model_improvement=False,leaderboard_gain=False),f,indent=2)
            return
        frozen=protocol.bundle(index);actual=json.loads((path.parent/'inputs.json').read_text());done=json.loads((path/'complete.json').read_text())
        if actual!=frozen or done.get('source_inputs_sha256')!=protocol.digest(frozen) or done.get('scripted') is not False:raise ValueError('live frozen chunk required')
        rs=[json.loads(x) for x in (path/'records.jsonl').read_text().splitlines()];events=[json.loads(x) for x in (path/'events.jsonl').read_text().splitlines()]
        verified=verify_chunk(frozen,rs,events,counter);rows+=rs;ids+=verified['response_ids'];calls+=verified['call_ids']
        ctx=max(ctx,verified['max_context']);completion=max(completion,verified['max_completion'])
    if len(rows)!=8 or len(set(ids))!=len(ids) or len(set(calls))!=len(calls):raise ValueError('complete independent assigned study required')
    bundle=dict(namespace=protocol.NAMESPACE,confirmation_observations_materialized=False,screen_jobs=protocol.schedule('screen'),screen_groups=protocol.bundle(0)['screen_groups'])
    inputs=a.output.with_suffix('.verified-inputs.json');records=a.output.with_suffix('.verified-records.json')
    with inputs.open('x') as f:json.dump(bundle,f)
    with records.open('x') as f:json.dump(rows,f)
    scorer=Path(__file__).with_name('assess.mjs')
    js="import {readFileSync,writeFileSync} from 'node:fs';import {assess} from "+json.dumps(scorer.as_uri())+";const r=assess(JSON.parse(readFileSync("+json.dumps(str(inputs))+")),JSON.parse(readFileSync("+json.dumps(str(records))+")));writeFileSync("+json.dumps(str(a.output))+",JSON.stringify(r,null,2),{flag:'wx'});"
    subprocess.run(['node','--input-type=module','-e',js],check=True)
    result=json.loads(a.output.read_text());complete=all(r['generation_tokens'] is not None and r['category'] not in ['provider','budget'] for r in rows)
    result.update(all_live_replies_verified=complete,actual_calls=len(calls),selection_passed=complete and result['screen_selection_passed'],max_accounted_context=ctx,max_completion_with_observations=completion,model_improvement=False,leaderboard_gain=False)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(assigned=8,actual_calls=len(calls),selection_passed=result['selection_passed'],full_rate_delta=result['full_rate_delta'])))

if __name__=='__main__':main()
