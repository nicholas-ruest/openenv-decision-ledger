"""Confirmation admission bound to a complete, independently replayed screen."""
import ast,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SCREEN_SOURCE='c1ceaa7a244e2425de86d37a3f611301b7b2e497'
METHODS={'finalization_protocol.py': '59c287a5c71697438f9f9f9539d85427d4d9adb0e24d4a59126749059d6c8e5d', 'caller.py': '89e690e6c55e22a65cf4bed84d5e91c5a8b26452ecfa858755b8c1cf83b15837', 'assemble.py': '283973ee988000cdeb53e852280915cfc1f5ce1c73ce5725330d8189272a0029', 'assess.mjs': '96b11c587c7d8786e17ca8f1861d333aad396560f584fe4231f1157d72954bb4', 'replay.py': '17955b942f88be8db53584b3d202a25201e27169e4aac95e3fd1188bfa8f3684'}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def need(ok,message):
    if not ok:raise ValueError(message)
def roles():
    return {f'chunk{i}.{kind}' for i in range(4) for kind in ('inputs','events','records','complete','supervision','verification')}|{'assessment','frozen_screen','qualification','tokenizer'}|{'source.'+n for n in METHODS}
def method_unchanged():
    before=ROOT/'research/software-public-pass-finalization-20261031'
    after=Path(__file__).resolve().parent
    need(sha(ROOT/'research/software-first-proposal-audit-20261031/finalization_policy.py')=='2fe424adbf9e9989ebb64dc8ca93604ce6040069111c1a70f39136324807eef5','controller method changed')
    def symbols(path):
        tree=ast.parse(path.read_text());out={}
        for n in ast.walk(tree):
            if isinstance(n,ast.FunctionDef):n.body=[x for x in n.body if not (isinstance(x,ast.Expr) and isinstance(x.value,ast.Call) and isinstance(x.value.func,ast.Name) and x.value.func.id=='require_gate_ready')]
            if isinstance(n,ast.Constant) and n.value in ('screen','confirmation'):n.value='PHASE'
        for node in tree.body:
            if isinstance(node,(ast.ClassDef,ast.FunctionDef)) and node.name in ('Trial','sampling_for'):out[node.name]=ast.dump(node)
            elif isinstance(node,ast.Assign):
                for t in node.targets:
                    if isinstance(t,ast.Name) and t.id in ('NAMESPACE','ARMS','SEEDS','SAMPLING'):out[t.id]=ast.dump(node.value)
        return out
    need(symbols(before/'finalization_protocol.py')==symbols(after/'confirmation_protocol.py'),'frozen trial/sampling changed')
def verify_gate(path,expected):
    need(isinstance(expected,str) and len(expected)==64 and sha(path)==expected,'exact screen admission lease required')
    gate=json.loads(Path(path).read_text())
    need(gate.get('kind')=='independently-replayed-screen-selection' and gate.get('screen_source')==SCREEN_SOURCE,'attested frozen screen required')
    items=gate['inventory'];need(len(items)==len(roles()) and {x['role'] for x in items}==roles(),'complete unique screen artifact inventory required')
    paths={x['role']:Path(x['path']) for x in items}
    for item in items:need(sha(item['path'])==item['sha256'],'screen artifact changed')
    for name,digest in METHODS.items():need(sha(paths['source.'+name])==digest,'screen source differs')
    need(sha(paths['tokenizer'])=='0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3','tokenizer differs')
    a=json.loads(paths['assessment'].read_text())
    need(a.get('phase')=='screen' and a.get('selection_passed') is True and a.get('screen_selection_passed') is True,'positive completed screen required')
    need(a.get('attempts')==8 and a.get('attempts_per_arm')==4 and a.get('all_live_replies_verified') is True and a.get('all_assigned_attempts_in_denominator') is True,'all assigned screen outcomes required')
    need(a.get('unknown_generation_usage_attempts')==0 and a.get('full_rate_delta',0)>0 and a.get('semantic_mean_delta',-1)>=0,'known usage and frozen positive criteria required')
    need(a.get('max_accounted_context',99999)<=24576 and a.get('max_completion_with_observations',99999)<=8192,'unchanged total budgets required')
    need({g['seed'] for g in a['groups']}=={3120000} and {g['arm'] for g in a['groups']}=={'standard_revision','public_pass_finalize'},'screen scope differs')
    qualification=json.loads(paths['qualification'].read_text())
    need(qualification.get('source')==SCREEN_SOURCE and qualification.get('caller_tests')==6 and qualification.get('native_and_shared_gates_unchanged') is True and qualification.get('case_lease_verified',{}).get('verified') is True,'original qualification required')
    need(a.get('controller_provenance_verified') is True and a.get('identical_initial_prompts_verified') is True and a.get('outcome_scope')=='model_plus_controller_system_attempts','controller-aware screen required')
    ids=[];calls=[];all_rows=[]
    for i in range(4):
        done=json.loads(paths[f'chunk{i}.complete'].read_text());proof=json.loads(paths[f'chunk{i}.verification'].read_text())
        need(done.get('scripted') is False and done.get('assigned_attempts')==done.get('recorded_attempts')==2,'completed live chunk required')
        need(proof.get('clean_shutdown') is True and proof.get('all_workers_stopped') is True,'independent complete replay required')
        rows=[json.loads(x) for x in paths[f'chunk{i}.records'].read_text().splitlines()]
        need(len(rows)==2 and all(type(x['generation_tokens']) is int and x['category'] not in ('provider','budget') for x in rows),'unknown or incomplete screen outcomes')
        need(sorted(proof['response_ids'])==sorted(x for row in rows for x in row['response_ids']),'replay reply identities differ')
        need(sorted(proof['call_ids'])==sorted(x for row in rows for x in row['call_ids']),'replay call identities differ')
        all_rows+=rows;ids+=proof['response_ids'];calls+=proof['call_ids']
    need(len(ids)==len(set(ids)) and len(calls)==len(set(calls)) and len(calls)==len(ids)==a['actual_calls'],'reused or missing calls/replies')
    frozen=json.loads(paths['frozen_screen'].read_text())
    need(frozen.get('source')==SCREEN_SOURCE and frozen.get('confirmation_materialized') is False,'original screen freeze required')
    inputs=json.loads(paths['chunk0.inputs'].read_text())
    bundle=dict(namespace=inputs['namespace'],confirmation_observations_materialized=False,screen_jobs=inputs['all_screen_jobs'],screen_groups=inputs['screen_groups'])
    js="import {readFileSync} from 'node:fs';import {assess} from "+json.dumps(paths['source.assess.mjs'].as_uri())+";const x=JSON.parse(readFileSync(0,'utf8'));console.log(JSON.stringify(assess(x.bundle,x.rows)));"
    scored=subprocess.run(['node','--input-type=module','-e',js],input=json.dumps(dict(bundle=bundle,rows=all_rows)),text=True,capture_output=True,check=True,timeout=15)
    recomputed=json.loads(scored.stdout)
    need(all(a.get(k)==v for k,v in recomputed.items()),'screen criteria/fitness changed')
    method_unchanged()
    return gate
