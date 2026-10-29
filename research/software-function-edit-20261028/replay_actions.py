"""Posthoc action re-encoding of saved modules, not a fresh model experiment."""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'research/software-function-edit-20261028'),str(ROOT/'integrations/software-repair')]
from function_edit import FunctionEditEnvironment,FunctionEditAction,TARGETS

def target_definition(code,target):
    nodes=[n for n in ast.parse(code).body if isinstance(n,ast.FunctionDef) and n.name==target]
    if len(nodes)!=1:raise ValueError('one saved target definition required')
    n=nodes[0];return ''.join(code.splitlines(keepends=True)[n.lineno-1:n.end_lineno])

def main(archive,output,expected_sha):
    raw=archive.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_sha:raise ValueError('externally supplied archive hash mismatch')
    rows=[json.loads(s) for s in raw.splitlines()]
    output.mkdir(exist_ok=False);pairs=[]
    for r in rows:
        a=json.loads(next(m['content'] for m in r['messages'] if m['role']=='assistant'))
        if set(a)=={'action'}:a=a['action']
        code=a['content'];definition=target_definition(code,TARGETS[r['task_id']])
        from repair_env.tasks import make_task
        supplied={n.name for n in ast.parse(make_task(r['task_id'],r['seed']).initial_source).body if isinstance(n,ast.FunctionDef)}
        for n in ast.parse(code).body:
            if isinstance(n,ast.FunctionDef) and n.name not in supplied:definition+='\n'+target_definition(code,n.name)
        observed={}
        for mode,text in [('module',code),('function',definition)]:
            e=FunctionEditEnvironment();e.reset(task_id=r['task_id'],seed=r['seed'])
            n=e.step(FunctionEditAction(mode=mode,content=text))
            observed[mode]=dict(reward=n.reward,error=bool(n.error),action_bytes=len(json.dumps(dict(mode=mode,content=text)).encode()))
        if abs(observed['module']['reward']-r['reward'])>1e-9:raise ValueError('legacy module grade drift')
        pairs.append(dict(task_id=r['task_id'],seed=r['seed'],sample=r['sample'],**observed))
    counts=lambda mode:dict(Counter('full' if p[mode]['reward']==1 else 'partial' if p[mode]['reward']>0 else 'zero' for p in pairs))
    result=dict(saved_modules=len(rows),procedural_seed_count=len({r['seed'] for r in rows}),module_outcomes=counts('module'),function_outcomes=counts('function'),
                posthoc_improved=sum(p['function']['reward']>p['module']['reward'] for p in pairs),
                posthoc_regressed=sum(p['function']['reward']<p['module']['reward'] for p in pairs),
                unchanged_module_grades=True,new_model_calls=0,fresh_confirmation=False,
                limit='Extracting a function from old full-module replies changes the action after generation. Not a model comparison, training gain or private transfer.')
    (output/'private-pairs.json').write_text(json.dumps(pairs,indent=2)+'\n')
    (output/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--expected-sha256',required=True)
    a=p.parse_args();main(a.archive,a.output,a.expected_sha256)
