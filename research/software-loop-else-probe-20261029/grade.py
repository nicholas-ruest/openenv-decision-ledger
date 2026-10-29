"""Score saved replies under one exact runtime; no inference or host code execution."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

def main():
    p=argparse.ArgumentParser()
    for name in ['runtime-root','archive','output','tokenizer']:p.add_argument('--'+name,type=Path,required=True)
    for name in ['expected-runtime','inputs-sha256']:p.add_argument('--'+name,required=True)
    a=p.parse_args();root=a.runtime_root
    if subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()!=a.expected_runtime:raise ValueError('runtime source changed')
    subprocess.run(['git','-C',str(root),'diff','--quiet','HEAD'],check=True)
    sys.path[:0]=[str(root/x) for x in ['integrations/software-repair','research/software-function-edit-20261028','research/software-terminal-audit-20261028','research/software-function-block-protocol-20261028']]
    from function_edit import FunctionEditEnvironment,FunctionEditAction
    from terminal_audit import classify
    from protocol import digest,canonical
    spec=importlib.util.spec_from_file_location('paired_runtime_counter',root/'integrations/openenv-arena/scripts/calibrate.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    counter=helper.load_counter(argparse.Namespace(accounting='arena',tokenizer_json=a.tokenizer,tokenizer_sha256='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3'))
    bundle=json.loads((a.archive/'inputs.json').read_text())
    if digest(bundle)!=a.inputs_sha256:raise ValueError('frozen inputs changed')
    rows=[json.loads(x) for x in (a.archive/'live/records.jsonl').read_text().splitlines()]
    events=[json.loads(x) for x in (a.archive/'live/events.jsonl').read_text().splitlines()]
    if len(rows)!=8 or [x['attempt_id'] for x in rows]!=[j['attempt_id'] for j in bundle['screen_jobs']]:raise ValueError('complete exact assignments required')
    replies={x['attempt_id']:x['response'] for x in events if x['event']=='response'}
    seen=set();out=[]
    for row in rows:
        result=dict(row,raw_response_sha256=None)
        reply=replies.get(row['attempt_id'])
        if reply is not None:
            identity=hashlib.sha256(reply['id'].encode()).hexdigest()
            if identity in seen or identity!=row['response_id'] or reply['usage']['completion_tokens']!=row['generation_tokens']:raise ValueError('response identity or usage mismatch')
            seen.add(identity);result['raw_response_sha256']=digest(reply)
        if row['category'] in ['full','partial','wrong','execution','edit_rejection']:
            if reply is None or row['finish_reason']!='stop':raise ValueError('complete reply required for native grade')
            env=FunctionEditEnvironment();env.reset(task_id=row['task_id'],seed=row['seed'])
            action=FunctionEditAction.model_validate_json(reply['choices'][0]['message']['content'],strict=True)
            native=env.step(action).model_dump()
            if native['error'].startswith('Invalid function edit;'):diagnosis=dict(category='edit_rejection',native_reward=native['reward'],semantic_reward=None)
            else:diagnosis=classify(env,native)
            result.update(category=diagnosis['category'],terminal_reward_observed=diagnosis['native_reward'],semantic_reward=diagnosis['semantic_reward'])
            obs_tokens=counter.count(canonical(native))
            group=next(g for g in bundle['screen_groups'] if g['task_id']==row['task_id'] and g['seed']==row['seed'])
            messages=group['arms']['function_block_available']['messages']+[reply['choices'][0]['message'],dict(role='user',content=canonical(native))]
            context=max(counter.context(messages),reply['usage']['prompt_tokens']+row['generation_tokens']+obs_tokens)
            result.update(observation_tokens=obs_tokens,accounted_context=context)
            if row['generation_tokens']+obs_tokens>4096 or context>8192:result.update(category='budget',semantic_reward=None)
        out.append(result)
    payload=dict(runtime=a.expected_runtime,inputs_sha256=a.inputs_sha256,assigned=8,rows=out,model_training=False,leaderboard_gain=False)
    with a.output.open('x') as f:json.dump(payload,f,indent=2)
    print(json.dumps(dict(assigned=8,responses=len(seen),full=sum(x['category']=='full' for x in out))))

if __name__=='__main__':main()
