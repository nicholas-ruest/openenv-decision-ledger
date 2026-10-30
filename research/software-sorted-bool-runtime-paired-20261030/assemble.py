"""Independent source/request/usage/paired-Native attestation before any selection."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
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
            request=dict(protocol.sampling_for(job,turn),messages=trial.messages,max_tokens=limit)
            if intent['request_sha256']!=protocol.digest(request) or intent['messages_sha256']!=protocol.digest(trial.messages):raise ValueError('sent request binding changed')
            identities.append(identity);generation+=usage['completion_tokens'];context=max(context,usage['prompt_tokens']+usage['completion_tokens'])
            choice=reply['choices'][0];finish=choice.get('finish_reason')
            if finish=='length':category='truncation';break
            if finish!='stop':category='provider';break
            value=trial.consume(choice['message'].get('content'))
            obs=counter.count(protocol.canonical(trial.native[-1])) if trial.native and len(trial.native)==turn+1 else 0
            observations+=obs;context=max(context,counter.context(trial.messages),usage['prompt_tokens']+usage['completion_tokens']+obs)
            category=value['category'];semantic=value.get('semantic_reward');reward=value['native_reward']
        if row['category']=='truncation' and row.get('paired_native') is not None:raise ValueError('truncated response has no Native grade')
        if replies and row['category'] not in ['provider','budget','truncation'] and row.get('paired_native')!=value.get('paired_native'):raise ValueError('paired Native replay changed')
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


def assess(rows):
 if len(rows)!=4 or [r['attempt_id'] for r in rows]!=[j['attempt_id'] for j in protocol.schedule('screen')]:
  raise ValueError('all four assigned samples required')
 counts={name:dict(full=0,semantic_sum=0,failures={}) for name in ('baseline','candidate')}
 exposed=0;lost=0;known=True
 for row in rows:
  known=known and row['generation_tokens'] is not None and row['category'] not in ('provider','budget')
  pair=row.get('paired_native')
  if pair is not None:
   if pair.get('actual_same_program') is not True:raise ValueError('actual shared program binding required')
   exposed+=int(pair['compatibility_exposure'])
   lost+=int(pair['baseline']['category']=='full' and pair['candidate']['category']!='full')
   values={k:pair[k] for k in counts}
  else:
   if row['category'] in ('full','partial','wrong','execution'):raise ValueError('Native paired result missing')
   values={k:dict(category=row['category'],semantic_reward=None) for k in counts}
  for name,value in values.items():
   count=counts[name];count['full']+=int(value['category']=='full')
   count['semantic_sum']+=value['semantic_reward'] or 0
   count['failures'][value['category']]=count['failures'].get(value['category'],0)+1
 delta=(counts['candidate']['full']-counts['baseline']['full'])/4
 semantic=(counts['candidate']['semantic_sum']-counts['baseline']['semantic_sum'])/4
 return dict(assigned=4,counts=counts,full_rate_delta=delta,semantic_mean_delta=semantic,
  compatibility_exposures=exposed,lost_baseline_full_solves=lost,all_usage_known=known,
  statistical_gate=known and delta>0 and semantic>=0 and lost==0 and exposed>0,
  model_improvement=False,leaderboard_gain=False,is_training=False)
def main():
 p=argparse.ArgumentParser();p.add_argument('--chunks',type=Path,nargs=2,required=True)
 p.add_argument('--output',type=Path,required=True);p.add_argument('--tokenizer',type=Path,required=True);p.add_argument('--expected-source',required=True);a=p.parse_args()
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==a.expected_source
 subprocess.run(['git','diff','--quiet','HEAD'],cwd=ROOT,check=True)
 helper=load('paired_native_counter',ROOT/'integrations/openenv-arena/scripts/calibrate.py')
 counter=helper.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=a.tokenizer,tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
 rows=[];identities=[];calls=[];maximum_context=0;maximum_completion=0
 for i,path in enumerate(a.chunks):
  if not (path/'complete.json').exists():
   result=dict(status='incomplete',assigned=4,recorded=len(rows),all_assigned_jobs=protocol.schedule('screen'),selection_passed=False,model_improvement=False,leaderboard_gain=False)
   with a.output.open('x') as f:json.dump(result,f,indent=2)
   return
  bundle=protocol.bundle(i);actual=json.loads((path.parent/'inputs.json').read_text());complete=json.loads((path/'complete.json').read_text())
  assert actual==bundle and complete['scripted'] is False and complete['source_inputs_sha256']==protocol.digest(bundle)
  current=[json.loads(l) for l in (path/'records.jsonl').read_text().splitlines()]
  events=[json.loads(l) for l in (path/'events.jsonl').read_text().splitlines()]
  proof=verify_chunk(bundle,current,events,counter);rows+=current;identities+=proof['response_ids'];calls+=proof['call_ids']
  maximum_context=max(maximum_context,proof['max_context']);maximum_completion=max(maximum_completion,proof['max_completion'])
 assert len(set(identities))==len(identities) and len(set(calls))==len(calls)
 result=assess(rows);result.update(source=a.expected_source,actual_calls=len(calls),known_replies=len(identities),paired_native_verified=True,
   max_context=maximum_context,max_generation_with_observations=maximum_completion,
   selection_passed=result['statistical_gate'] and len(identities)==4,confirmation_materialized=False)
 # Actual pinned MetaHarness classifier is descriptive per runtime. Calls/cost are counted once.
 meta={}
 if result['all_usage_known']:
  failure={'execution':'environment_step_failed','format':'invalid_json_action','edit_rejection':'invalid_json_action','truncation':'completion_truncated','provider':'provider_request_failed','budget':'global_token_budget_exhausted'}
  adapter=ROOT/'research/metaharness-compatibility-20261028/adapter.mjs'
  for runtime in ('baseline','candidate'):
   episodes=[]
   for row in rows:
    value=(row.get('paired_native') or {}).get(runtime,row);cat=value['category'];reward=value.get('semantic_reward')
    episodes.append(dict(type='episode',seed=row['seed'],attempt=row['sample'],reward=reward or 0,failure=failure.get(cat),
       trajectory=dict(accounting=dict(generation_tokens=row['generation_tokens']),provider_metrics=[dict(finish_reason=row['finish_reason'])])))
   js="import {scoreCell,PIN} from "+json.dumps(adapter.as_uri())+";console.log(JSON.stringify({pin:PIN,score:scoreCell("+json.dumps(episodes)+")}));"
   meta[runtime]=json.loads(subprocess.check_output(['node','--input-type=module','-e',js],text=True))
 result['metaharness']=meta;result['cost_counted_once']=True
 with a.output.open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result))
if __name__=='__main__':main()
