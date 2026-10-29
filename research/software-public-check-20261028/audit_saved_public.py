"""Run the public checker on a frozen saved archive, without provider calls."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from public_check import feedback


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('runtime-root','probe-root','archive','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('fresh private output required')
    pins=json.loads((a.probe_root/'config/software-probe-source-hashes-20261027.json').read_text())
    for n,sha in pins.items():
        if hashlib.sha256((a.runtime_root/n).read_bytes()).hexdigest()!=sha:raise ValueError('frozen interpreter/runtime drift')
    spec=importlib.util.spec_from_file_location('public_check_frozen_base',a.runtime_root/'scripts/repair-signal-screen.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
    raw=a.archive/'raw-episodes.jsonl';rows=[json.loads(l) for l in raw.read_text().splitlines() if l]
    if len(rows)!=16:raise ValueError('existing completed16 archive required')
    checked=[]
    for row in rows:
        reset=json.loads(row['messages'][1]['content'])
        reply=json.loads(next(m['content'] for m in row['messages'] if m['role']=='assistant'))
        if set(reply)=={'action'}:reply=reply['action']
        result=feedback({'examples':reset['examples']},reply['content'],base.Program)
        checked.append({'task_id':row['task_id'],'seed':row['seed'],'sample':row['sample'],'public_feedback':result})
    report={'archive_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'checked':checked,'public_only':True,'hidden_access':False,'new_model_calls':0,'revised_responses':0}
    with a.output.open('x') as f:json.dump(report,f,indent=2)
    print(json.dumps({'checked':len(checked),'public_passed_counts':[r['public_feedback'].get('passed') for r in checked],'execution_errors':sum(r['public_feedback'].get('execution_errors',0) for r in checked),'new_model_calls':0}))

if __name__=='__main__':main()
