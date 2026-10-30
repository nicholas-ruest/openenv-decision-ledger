"""Offline Native regrading of complete saved modules; no provider or host model-code execution."""
import argparse,hashlib,json,sys
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--app-root',type=Path,required=True);p.add_argument('--runner-sha256',required=True)
 p.add_argument('--screen',type=Path,required=True);p.add_argument('--confirmation',type=Path,required=True)
 p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 app=a.app_root.resolve();sys.path.insert(0,str(app))
 from repair_env.direct_environment import DirectRepairEnvironment,DirectRepairAction
 from repair_env.environment import check
 from repair_env.runner import Program,Rejected
 import repair_env.runner as runner
 assert Path(runner.__file__).resolve()==app/'repair_env/runner.py'
 assert sha(Path(runner.__file__))==a.runner_sha256
 out=[]
 for phase,archive in [('screen',a.screen),('confirmation',a.confirmation)]:
  for i in range(4):
   parent=archive/f'chunk{i}';live=parent/'live'
   events=[json.loads(x) for x in (live/'events.jsonl').read_text().splitlines()]
   inputs=json.loads((parent/'inputs.json').read_text())
   for row in [json.loads(x) for x in (live/'records.jsonl').read_text().splitlines()]:
    result=dict(phase=phase,sample=i,arm=row['arm'],attempt_id=row['attempt_id'],
      original_category=row['category'],original_reward=row['semantic_reward'])
    if row['category'] in ('provider','budget','truncation','format','edit_rejection'):
     out.append(dict(result,regraded=False,reason='Original failure remains assigned; no reconstruction'));continue
    replies=[x['response']['choices'][0] for x in events if x['event']=='response' and x['attempt_id']==row['attempt_id']]
    assert len(replies)==2 and all(x['finish_reason']=='stop' for x in replies)
    env=DirectRepairEnvironment();reset=env.reset(task_id=row['task_id'],seed=row['seed'])
    groups=inputs.get('screen_groups',inputs.get('confirmation_groups'))
    assert groups
    original=json.loads(groups[0]['arms'][row['arm']]['messages'][1]['content'])
    assert reset.source==original['source'] and reset.examples==original['examples']
    source=reset.source
    for reply in replies:
     action=json.loads(reply['message']['content']);assert type(action) is dict
     text=action.get('content','');assert type(text) is str
     source=text or source
    terminal=env.step(DirectRepairAction(content=source));errors=0;compile_rejected=False
    try:
     program=Program(source)
     passed,details=check(program,env._task,env._task.hidden,details=True)
     errors=sum(x['error'] is not None for x in details)
     if terminal.reward==1:assert passed==len(env._task.hidden)
    except (Rejected,RecursionError):compile_rejected=True
    category=('execution' if terminal.error or compile_rejected or errors else
              'full' if terminal.reward==1 else 'partial' if terminal.reward>0 else 'wrong')
    out.append(dict(result,regraded=True,source_sha256=hashlib.sha256(source.encode()).hexdigest(),
       category=category,semantic_reward=None if category=='execution' else terminal.reward,
       compile_rejected=compile_rejected,hidden_execution_errors=errors))
 assert len(out)==16
 value=dict(posthoc=True,model_calls=0,assigned=16,runner_sha256=a.runner_sha256,
    runtime_files={str(x.relative_to(app)):sha(x) for x in (app/'repair_env').glob('*.py')},
    records=out,fresh_improvement=False,leaderboard_gain=False)
 with a.output.open('x') as f:json.dump(value,f,indent=2)
 print(json.dumps(dict(assigned=16,regraded=sum(x['regraded'] for x in out),
    full=sum(x.get('category')=='full' for x in out),model_calls=0)))
if __name__=='__main__':main()
