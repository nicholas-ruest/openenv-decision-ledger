"""Offline localization of saved software repairs. Never executes model code on host."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path


def functions(source):
    tree=ast.parse(source)
    funcs={}
    for node in tree.body:
        if isinstance(node,ast.FunctionDef):
            if node.name in funcs:raise ValueError('duplicate function identity')
            funcs[node.name]=node
    return funcs


def same_function(a,b):return ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)


def restore(candidate,supplied,names):
    """Posthoc counterfactual using supplied public code, not a model solve."""
    original=functions(supplied);tree=ast.parse(candidate);present=functions(candidate)
    if not set(names)<=original.keys() or not set(names)<=present.keys():raise ValueError('existing supplied function required')
    tree.body=[copy.deepcopy(original[n.name]) if isinstance(n,ast.FunctionDef) and n.name in names else n for n in tree.body]
    return ast.unparse(ast.fix_missing_locations(tree))+'\n'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('runtime-root','probe-root','archive','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('fresh diagnosis output required')
    pins=json.loads((a.probe_root/'config/software-probe-source-hashes-20261027.json').read_text())
    for name,sha in pins.items():
        if hashlib.sha256((a.runtime_root/name).read_bytes()).hexdigest()!=sha:raise ValueError('frozen dependency drift')
    base=load('frozen_partial_base',a.runtime_root/'scripts/repair-signal-screen.py')
    from repair_env.environment import check,semantic_fields
    raw_path=a.archive/'raw-episodes.jsonl';rows=[json.loads(l) for l in raw_path.read_text().splitlines() if l]
    if len(rows)!=16:raise ValueError('completed legacy16 archive required')
    reports=[]
    for row in rows:
        if row['failure'] is not None:continue
        env=base.DirectRepairEnvironment();env.reset(task_id=row['task_id'],seed=row['seed']);task=env._task
        reply=next(m for m in row['messages'] if m['role']=='assistant');action=json.loads(reply['content'])
        if set(action)=={'action'}:action=action['action']
        code=action['content'];native=env.step(base.DirectRepairAction(content=code))
        if native.error or float(native.reward)!=row['reward']:raise ValueError('saved semantic reward does not replay')
        original=functions(task.initial_source);candidate=functions(code)
        supplied_names=['match_segment','match_parts','rule_mode' if row['task_id'].endswith('d3') else 'classify_ignore']
        changed=[n for n in supplied_names if n not in candidate or not same_function(original[n],candidate[n])]
        def score(source):
            program=base.Program(source);passed,details=check(program,task,task.hidden,details=True)
            pub,public=check(program,task,task.public,details=True)
            return {'hidden_passed':passed,'hidden_total':len(details),'public_passed':pub,'public_total':len(public),
                    'hidden_fields':semantic_fields(details),'execution_errors':sum(d['error'] is not None for d in details)},details
        baseline,details=score(code)
        interventions={}
        for names in [[n] for n in changed if n in candidate]+([changed] if len(changed)>1 and all(n in candidate for n in changed) else []):
            key='+'.join(names)
            try:interventions[key]=score(restore(code,task.initial_source,names))[0]
            except Exception as exc:interventions[key]={'error_type':type(exc).__name__}
        reports.append({'task_id':row['task_id'],'seed':row['seed'],'sample':row['sample'],'saved_reward':row['reward'],
            'changed_supplied_functions':changed,'baseline':baseline,'restoring_public_supplied_functions':interventions,
            'private_failed_cases':[d for d in details if not d['passed']]})
    result={'archive_sha256':hashlib.sha256(raw_path.read_bytes()).hexdigest(),'records_replayed':len(reports),
        'new_model_calls':0,'posthoc_diagnostic_only':True,'confirmation':False,'private_records':reports}
    with a.output.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps({'records_replayed':len(reports),'partial':[dict(task=r['task_id'],seed=r['seed'],sample=r['sample'],changed=r['changed_supplied_functions'],baseline=r['baseline'],restoration=r['restoring_public_supplied_functions']) for r in reports if r['saved_reward']<1],'new_model_calls':0}))


if __name__=='__main__':main()
