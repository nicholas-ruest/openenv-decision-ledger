"""Verify four fresh chunks before scoring a complete native-budget study."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/x) for x in ['research/software-native-helper8k-20261029','research/software-function-trial-20261029','integrations/openenv-arena']]
import native_protocol as protocol
from caller import load
from trial import Trial

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--chunks',type=Path,nargs=4,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--tokenizer',type=Path,required=True)
    p.add_argument('--expected-source',required=True);a=p.parse_args()
    if subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()!=a.expected_source:raise ValueError('source differs')
    subprocess.run(['git','-C',str(ROOT),'diff','--quiet','HEAD'],check=True)
    helper=load('native_study_counter',ROOT/'integrations/openenv-arena/scripts/calibrate.py')
    counter=helper.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=a.tokenizer,tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
    all_rows=[];identities=set();calls=set();contexts=[];completions=[]
    for index,path in enumerate(a.chunks):
        frozen=protocol.bundle(index)
        if not (path/'complete.json').exists():
            with a.output.open('x') as f:json.dump(dict(status='inconclusive_incomplete_experiment',assigned=16,completed_chunks=index,all_assigned_jobs=protocol.schedule('screen'),selection_passed=False,model_improvement=False,leaderboard_gain=False),f,indent=2)
            return
        actual=json.loads((path.parent/'inputs.json').read_text())
        completed=json.loads((path/'complete.json').read_text())
        rows=[json.loads(x) for x in (path/'records.jsonl').read_text().splitlines()]
        events=[json.loads(x) for x in (path/'events.jsonl').read_text().splitlines()]
        if (actual!=frozen or completed.get('source_inputs_sha256')!=protocol.digest(frozen)
                or completed.get('scripted') is not False or completed.get('recorded_attempts')!=4
                or len(rows)!=4 or [r['attempt_id'] for r in rows]!=[j['attempt_id'] for j in frozen['screen_jobs']]):raise ValueError('chunk binding differs')
        replies={e['attempt_id']:e['response'] for e in events if e['event']=='response'}
        for row in rows:
            reply=replies.get(row['attempt_id'])
            if row['call_id'] is not None:
                if row['call_id'] in calls:raise ValueError('reused call identity')
                calls.add(row['call_id'])
            if reply is None:
                if row['response_id'] is not None or row['category'] not in ['provider','budget']:raise ValueError('missing semantic reply')
                all_rows.append(row);continue
            identity=hashlib.sha256(reply['id'].encode()).hexdigest()
            if identity in identities or identity!=row['response_id']:raise ValueError('reused response identity')
            identities.add(identity)
            usage=reply['usage']
            if usage['completion_tokens']!=row['generation_tokens']:raise ValueError('usage changed')
            group=next(g for g in frozen['screen_groups'] if g['task_id']==row['task_id'] and g['seed']==row['seed'])
            request=group['arms'][row['arm']]
            if row['category'] not in ['provider','budget']:
                job=next(j for j in frozen['screen_jobs'] if j['attempt_id']==row['attempt_id'])
                trial=Trial(job,request['prompt_sha256'],request['problem_sha256'],binding_factory=protocol.Binding)
                choice=reply['choices'][0];value=trial.consume(choice['message'].get('content'),finish_reason=choice.get('finish_reason'))
                obs=counter.count(protocol.canonical(trial.native)) if trial.native is not None else 0
                context=usage['prompt_tokens']+row['generation_tokens']+obs
                if trial.native is not None:
                    messages=trial.messages+[choice['message'],dict(role='user',content=protocol.canonical(trial.native))]
                    context=max(context,counter.context(messages))
                if (value['category'],value['native_reward'],value['semantic_reward'])!=(row['category'],row['terminal_reward_observed'],row['semantic_reward']):raise ValueError('native replay differs')
                if obs!=row['observation_tokens'] or row['generation_tokens']+obs>8192 or context>24576:raise ValueError('native token accounting differs')
                contexts.append(context);completions.append(row['generation_tokens']+obs)
            all_rows.append(row)
    if len(all_rows)!=16 or [r['attempt_id'] for r in all_rows]!=[j['attempt_id'] for j in protocol.schedule('screen')]:raise ValueError('complete sixteen-assignment denominator required')
    analysis=dict(namespace=protocol.NAMESPACE,screen_jobs=protocol.schedule('screen'),screen_groups=protocol.bundle(0)['screen_groups'],confirmation_observations_materialized=False)
    interim=a.output.with_suffix('.verified-inputs.json');records=a.output.with_suffix('.verified-records.json')
    with interim.open('x') as f:json.dump(analysis,f)
    with records.open('x') as f:json.dump(all_rows,f)
    scorer=Path(__file__).with_name('assess.mjs')
    js="import {readFileSync,writeFileSync} from 'node:fs';import {assess} from "+json.dumps(scorer.as_uri())+";const r=assess(JSON.parse(readFileSync("+json.dumps(str(interim))+")),JSON.parse(readFileSync("+json.dumps(str(records))+")));writeFileSync("+json.dumps(str(a.output))+",JSON.stringify(r,null,2),{flag:'wx'});"
    subprocess.run(['node','--input-type=module','-e',js],check=True)
    result=json.loads(a.output.read_text())
    complete=len(calls)==len(identities)==16 and all(r['generation_tokens'] is not None and r['category'] not in ['provider','budget'] for r in all_rows)
    result.update(all_live_replies_verified=complete,selection_passed=complete and result['screen_selection_passed'],max_accounted_context=max(contexts,default=0),max_completion_with_observations=max(completions,default=0),model_improvement=False,leaderboard_gain=False)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(assigned=16,replies=len(identities),selection_passed=result['selection_passed'],full_rate_delta=result['full_rate_delta'],semantic_mean_delta=result['semantic_mean_delta'])))

if __name__=='__main__':main()
