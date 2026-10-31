"""Independently replay the complete computed-feedback screen before selection."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from caller import ROOT,modules,load
verify_chunk=load('exact_finalization_replay',Path(__file__).with_name('replay.py')).verify_chunk
protocol,Trial=modules()

def load_live_chunk(index,path,counter):
    frozen=protocol.bundle(index)
    actual=json.loads((path.parent/'inputs.json').read_text())
    done=json.loads((path/'complete.json').read_text())
    if actual!=frozen or done.get('source_inputs_sha256')!=protocol.digest(frozen) or done.get('scripted') is not False:
        raise ValueError('live frozen chunk required')
    rows=[json.loads(x) for x in (path/'records.jsonl').read_text().splitlines()]
    events=[json.loads(x) for x in (path/'events.jsonl').read_text().splitlines()]
    return rows,verify_chunk(frozen,rows,events,counter)


def main():
    p=argparse.ArgumentParser();p.add_argument('--chunks',type=Path,nargs=4,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--tokenizer',type=Path,required=True);p.add_argument('--expected-source',required=True);a=p.parse_args()
    if subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()!=a.expected_source:raise ValueError('source differs')
    subprocess.run(['git','-C',str(ROOT),'diff','--quiet','HEAD'],check=True)
    if subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'],text=True).strip():
        raise ValueError('clean source worktree required')
    helper=load('feedback_replay_counter',ROOT/'integrations/openenv-arena/scripts/calibrate.py')
    counter=helper.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=a.tokenizer,tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
    rows=[];ids=[];calls=[];ctx=0;completion=0
    for index,path in enumerate(a.chunks):
        if not (path/'complete.json').exists():
            with a.output.open('x') as f:json.dump(dict(status='inconclusive_incomplete_experiment',assigned=8,completed_chunks=index,all_assigned_jobs=protocol.schedule('screen'),selection_passed=False,model_improvement=False,leaderboard_gain=False),f,indent=2)
            return
        rs,verified=load_live_chunk(index,path,counter);rows+=rs;ids+=verified['response_ids'];calls+=verified['call_ids']
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
    result.update(identical_initial_prompts_verified=True,controller_provenance_verified=True,all_live_replies_verified=complete,actual_calls=len(calls),selection_passed=complete and result['screen_selection_passed'],max_accounted_context=ctx,max_completion_with_observations=completion,model_improvement=False,leaderboard_gain=False)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(assigned=8,actual_calls=len(calls),selection_passed=result['selection_passed'],full_rate_delta=result['full_rate_delta'])))

if __name__=='__main__':main()
