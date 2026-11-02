"""Replay closed first proposals on their supplied examples; no inference or new cases.

Submitted modules run only in the original bounded Native interpreter. Output is
sanitized: no trajectories, case inputs, private file paths or raw input hashes.
"""
import argparse,ast,copy,hashlib,json,re,subprocess,sys
from pathlib import Path

PINS={'runner.py':'fcb0f8b5cb5321ae998f71a38502125a595cc39d6b6331eedd659ba9ceed65a6',
      'environment.py':'248b3fc62b36b49f6a23ab694674c5fe1e0397528b55f039cf6064462a6c9e85'}

def functions(code):return {n.name:n for n in ast.parse(code).body if isinstance(n,ast.FunctionDef)}
def structure(code,exclude):
    return [ast.dump(n,include_attributes=False) for n in ast.parse(code).body
            if not isinstance(n,ast.FunctionDef) or n.name!=exclude]

def analyze(archive,helper_name):
    archive=Path(archive).resolve();source=archive/'source'
    meta=json.loads((archive/'execution-source.json').read_text())
    if (subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()!=meta['source']
        or subprocess.check_output(['git','status','--porcelain'],cwd=source,text=True).strip()):
        raise ValueError('original clean recorded source required')
    native=source/'integrations/software-repair/repair_env'
    for name,expected in PINS.items():
        if hashlib.sha256((native/name).read_bytes()).hexdigest()!=expected:raise ValueError('original Native source differs')
    sys.path.insert(0,str(native.parent))
    from repair_env.runner import Program
    # Execute only this trusted, pinned framework function, never submitted Python.
    node=functions((native/'environment.py').read_text())['exact'];ns={}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(native/'environment.py'),'exec'),ns)
    exact=ns['exact']
    closed=json.loads((archive/'closed-independent-verification.json').read_text())
    if not closed['supervisor']['shutdown_verified']:raise ValueError('closed original worker required')
    prior=json.loads((archive/'closed-posthoc-proposal-diagnosis.json').read_text())
    jobs=json.loads((archive/'screen/assignments.json').read_text());snapshots={};rows=[];first_codes=[];helper_asts=[]
    def read(path):
        raw=path.read_bytes();snapshots[path]=hashlib.sha256(raw).hexdigest();return json.loads(raw)
    def grade(code,examples):
        program=Program(code);passed=0;errors=[]
        for args,expected in examples:
            try:passed+=exact(program.run('classify_ignore',copy.deepcopy(args)),expected)
            except Exception as exc:errors.append(type(exc).__name__)
        return dict(public_passes=passed,runtime_errors=len(errors),runtime_error_types=sorted(set(errors)))
    for job in jobs:
        if not any(r.get('posthoc_first_category')=='execution' and r['arm']==job['arm'] and r['sample']==job['sample'] for r in prior['rows']):continue
        if not re.fullmatch('[a-f0-9]{64}',job['attempt_id']):raise ValueError('original assignment identity required')
        folder=archive/'screen'/job['attempt_id'];obs=json.loads(read(folder/'request-0.json')['messages'][1]['content'])
        examples=ast.literal_eval(obs['examples'])
        if len(examples)!=6:raise ValueError('six supplied public examples required')
        codes=[json.loads(read(folder/('response-'+str(turn)+'.json'))['choices'][0]['message']['content'])['content'] for turn in (0,1)]
        original=functions(obs['source'])[helper_name];changed=functions(codes[0])[helper_name]
        if helper_name=='classify_ignore':raise ValueError('supplied non-entrypoint helper required')
        lines=codes[0].splitlines(keepends=True)
        control=''.join(lines[:changed.lineno-1])+ast.get_source_segment(obs['source'],original)+'\n'+''.join(lines[changed.end_lineno:])
        if structure(control,helper_name)!=structure(codes[0],helper_name):raise ValueError('other module statements changed')
        first_codes.append(codes[0]);helper_asts.append(ast.dump(changed,include_attributes=False))
        rows.append(dict(arm=job['arm'],public_examples=6,first=grade(codes[0],examples),
            restored_helper_control=grade(control,examples),saved_final=grade(codes[1],examples),
            only_supplied_helper_restored=True,all_other_module_statements_ast_unchanged=True))
    if not rows or any(hashlib.sha256(p.read_bytes()).hexdigest()!=h for p,h in snapshots.items()):raise ValueError('original archive changed')
    return dict(kind='closed_first_proposal_public_runtime_audit',rows=rows,distinct_first_modules=len(set(first_codes)),
        distinct_failing_helper_asts=len(set(helper_asts)),original_files_unchanged_during_replay=True,
        native_source_pins=PINS,public_examples_only=True,hidden_cases_replayed=False,
        posthoc_investigator_control=True,new_model_calls=0,new_cases=0,selection_decision_changed=False,
        closed_preservation_studies_reopened=False,model_improvement=False,is_training=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True);p.add_argument('--helper-name',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('fresh diagnosis output required')
    value=analyze(a.archive,a.helper_name)
    with a.output.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
    print(json.dumps(value))
