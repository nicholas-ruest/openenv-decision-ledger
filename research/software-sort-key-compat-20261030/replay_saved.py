import sys,json,hashlib,importlib.util
from pathlib import Path
import argparse
parser=argparse.ArgumentParser(description='Replay saved responses only in bounded interpreters; posthoc, no paid calls.')
for name in ('baseline-root','candidate-root','archive','output'):parser.add_argument('--'+name,type=Path,required=True)
args=parser.parse_args()
old=args.baseline_root;candidate=args.candidate_root;archive=args.archive
assert not args.output.exists()
sys.path.insert(0,str(old/'integrations/software-repair'))
import repair_env.environment as native
from repair_env.direct_environment import DirectRepairEnvironment,DirectRepairAction
from repair_env.runner import Program as OldProgram,Rejected as OldRejected
path=candidate/'integrations/software-repair/repair_env/runner.py'
spec=importlib.util.spec_from_file_location('candidate_runner',path)
new=importlib.util.module_from_spec(spec);spec.loader.exec_module(new)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
reports=[]
for chunk in range(4):
 records=[json.loads(l) for l in (archive/f'chunk{chunk}/live/records.jsonl').read_text().splitlines()]
 events=[json.loads(l) for l in (archive/f'chunk{chunk}/live/events.jsonl').read_text().splitlines()]
 for record in records:
  native.Program=OldProgram;native.Rejected=OldRejected
  env=DirectRepairEnvironment();env.reset(task_id=record['task_id'],seed=record['seed'])
  core=env._core;task=env._task;code=env._files['src/solution.py']
  responses=sorted([e for e in events if e['event']=='response' and e['attempt_id']==record['attempt_id']],key=lambda x:x['turn'])
  assert len(responses)==2
  for response in responses:
   action=json.loads(response['response']['choices'][0]['message']['content'])
   if action.get('content'):code=action['content']
   results={}
   for name,Program,Rejected in [('old',OldProgram,OldRejected),('candidate',new.Program,new.Rejected)]:
    native.Rejected=Rejected
    try:
     program=Program(code)
     passed,details=native.check(program,task,task.hidden,details=True)
     public,_=native.check(program,task,task.public,details=True)
     reward=0.0
     if program.fingerprint!=core._original.fingerprint:
      if passed==len(task.hidden):reward=1.0
      elif core._component_baseline is not None:
       improved=native.semantic_fields(details)-core._component_baseline
       if improved>0:reward=min(.95,improved/(core._component_total-core._component_baseline))
      elif passed>core._baseline:reward=min(.95,(passed-core._baseline)/(len(task.hidden)-core._baseline))
     native.Program=Program
     direct=DirectRepairEnvironment();direct.reset(task_id=record['task_id'],seed=record['seed'])
     assert direct._task==task
     terminal=direct.step(DirectRepairAction(content=code))
     assert abs(float(terminal.reward)-reward)<1e-10
     results[name]=dict(native_direct_verified=True,accepted=True,native_reward=reward,hidden_passed=passed,hidden_total=len(task.hidden),public_passed=public,errors=sum(bool(d['error']) for d in details))
    except (Rejected,RecursionError) as exc:
     results[name]=dict(accepted=False,native_reward=0.0,error_type=type(exc).__name__)
   if response['turn']==1 and record['semantic_reward'] is not None:
    assert abs(results['old']['native_reward']-record['semantic_reward'])<1e-10
   reports.append(dict(chunk=chunk,arm=record['arm'],sample=record['sample'],turn=response['turn'],source_sha256=hashlib.sha256(code.encode()).hexdigest(),**results))
assert len(reports)==16
files=[archive/f'chunk{n}/live/{name}.jsonl' for n in range(4) for name in ('records','events')]
result=dict(archive_sha256={str(p.relative_to(archive)):sha(p) for p in files},kind='posthoc_language_compatibility_replay',fresh_model_calls=0,training=False,old_runner_sha256=sha(old/'integrations/software-repair/repair_env/runner.py'),candidate_runner_sha256=sha(path),rows=reports)
with args.output.open('x') as f:json.dump(result,f,indent=2)
print(json.dumps([r for r in reports if r['turn']==1]))
