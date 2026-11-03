"""Replay the two remaining semantic partials on saved public examples only."""
import argparse,ast,copy,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path

def analyze(archive,runtime,expected,depth_candidate=False):
    archive=Path(archive).resolve();runtime=Path(runtime).resolve()
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=runtime,text=True).strip()!=expected or subprocess.check_output(['git','status','--porcelain'],cwd=runtime,text=True).strip():raise ValueError('exact clean Native source required')
    sys.path.insert(0,str(runtime/'integrations/software-repair'))
    from repair_env.runner import Program
    from repair_env.environment import exact
    if depth_candidate:
        path=Path(__file__).resolve().parents[2]/'research/software-value-depth-candidate-20261102/candidate.py'
        spec=importlib.util.spec_from_file_location('isolated_value_depth',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        _,alternative=module.load_pair(runtime);Program=alternative.Program
    snapshots={}
    def read(path,lines=False):
        raw=path.read_bytes();snapshots[path]=hashlib.sha256(raw).hexdigest()
        return [json.loads(x) for x in raw.splitlines() if x.strip()] if lines else json.loads(raw)
    closed=read(archive/'closure-proof.json')
    frozen=read(archive/'frozen-confirmation.json');historical=frozen['source']
    if closed.get('assigned')!=8 or closed.get('all_workers_stopped') is not True or historical!='4d69e68c55715d32699f155f068b38a77b8d6d8f':raise ValueError('original closed source and worker closure required')
    records=read(archive/'assessment.verified-records.json');selected=[r for r in records if r['category']=='partial' and r['sample']==3]
    if len(selected)!=2 or len(records)!=8 or any(r['phase']!='confirmation' or r['task_id']!='software_repair-ignore-d3' or r['seed']!=2910000 for r in selected):raise ValueError('original closed confirmation inventory required')
    rows=[]
    for source in sorted(archive.glob('chunk*/live/records.jsonl')):
        launch=read(source.parents[1]/'launch.json')
        if launch.get('source')!=historical:raise ValueError('original launch source differs')
        local=read(source,True);events=read(source.with_name('events.jsonl'),True);inputs=read(source.parents[1]/'inputs.json')
        for record in local:
            if record['attempt_id'] not in {r['attempt_id'] for r in selected}:continue
            if record not in selected:raise ValueError('original semantic-partial record changed')
            responses=[e['response'] for e in events if e['event']=='response' and e['attempt_id']==record['attempt_id']]
            if len(responses)!=2 or any(r['choices'][0]['finish_reason']!='stop' for r in responses):raise ValueError('original two completed replies required')
            ids=[hashlib.sha256(r['id'].encode()).hexdigest() for r in responses]
            if ids!=record['response_ids']:raise ValueError('original saved response identities required')
            group=next(g for g in inputs['confirmation_groups'] if g['task_id']==record['task_id'] and g['seed']==record['seed']);messages=group['arms'][record['arm']]['messages'];obs=json.loads(messages[1]['content'])
            if len(obs['examples'])>16000:raise ValueError('saved public examples bound')
            examples=ast.literal_eval(obs['examples'])
            if len(examples)!=6:raise ValueError('six originally supplied public examples required')
            codes=[json.loads(r['choices'][0]['message']['content']).get('content','') for r in responses];code=next((s for s in reversed(codes) if s),obs['source']);out=dict(arm=record['arm'],sample=record['sample'],program_sha256=hashlib.sha256(code.encode()).hexdigest(),public_examples=6,compile_accepted=False,public_passes=0,runtime_errors=[],wrong_examples=[])
            try:program=Program(code)
            except Exception as e:out['compile_error']=dict(type=type(e).__name__,message=str(e))
            else:
                out['compile_accepted']=True
                for index,(args,expected_answer) in enumerate(examples):
                    try:
                        value=program.run('classify_ignore',copy.deepcopy(args))
                        if exact(value,expected_answer):out['public_passes']+=1
                        else:out['wrong_examples'].append(index+1)
                    except Exception as e:out['runtime_errors'].append(dict(public_example=index+1,type=type(e).__name__,message=str(e)))
            rows.append(out)
    if len(rows)!=2 or any(hashlib.sha256(p.read_bytes()).hexdigest()!=h for p,h in snapshots.items()):raise ValueError('complete unchanged retained source required')
    pins={n:hashlib.sha256((runtime/'integrations/software-repair/repair_env'/n).read_bytes()).hexdigest() for n in ('runner.py','environment.py','tasks.py')}
    return dict(kind='retained_final_execution_public_replay',runtime_source=expected,recorded_execution_source=historical,isolated_depth_candidate_applied=depth_candidate,native_source_sha256=pins,rows=rows,underlying_cases=1,public_examples_only=True,hidden_cases_replayed=False,saved_archives_unchanged=True,original_selection_changed=False,new_model_calls=0,new_cases=0,model_improvement=False,is_training=False)

def main():
    p=argparse.ArgumentParser(allow_abbrev=False);p.add_argument('--archive',type=Path,required=True);p.add_argument('--runtime',type=Path,required=True);p.add_argument('--expected-source',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--depth-candidate',action='store_true');a=p.parse_args()
    if a.output.exists():raise ValueError('fresh private output required')
    value=analyze(a.archive,a.runtime,a.expected_source,a.depth_candidate)
    with a.output.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
    print(json.dumps(dict(rows=len(value['rows']),compile_accepted=[r['compile_accepted'] for r in value['rows']],public_passes=[r['public_passes'] for r in value['rows']],runtime_error_types=[sorted(set(e['type']+': '+e['message'] for e in r['runtime_errors'])) for r in value['rows']],compile_errors=[r.get('compile_error') for r in value['rows']],new_model_calls=0)))
if __name__=='__main__':main()
