"""Confirmation admission bound to a complete, independently replayed screen."""
import ast,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SCREEN_SOURCE='715c0d8f5854e920343eb5f09e208c7b2a97394c'
METHODS={"feedback_protocol.py":"986f134c315468bc4a31df5c144d0e392c24530771c5f080865ce1a2c2c8dd83","caller.py":"15bc4f80c90e8f665bd09719b9abf447d132e3008ffbd80edcb9357ab6496e52","assemble.py":"3a8339d91c9bd790a812d3f5dc3483677796859ca2296c25bbb263997844672e","assess.mjs":"f1b7c4a8b747e1486120fdf5c95e8be5717209fa82fae25c0bccb53758b5b1b6"}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def need(ok,message):
    if not ok:raise ValueError(message)
def roles():
    return {f'chunk{i}.{kind}' for i in range(4) for kind in ('inputs','events','records','complete','supervision','verification')}|{'assessment','frozen_screen','qualification','tokenizer'}|{'source.'+n for n in METHODS}
def method_unchanged():
    before=ROOT/'research/software-revision-thinking-d3-20261030'
    after=Path(__file__).resolve().parent
    for name in ('mandatory_environment.py','joint_revision_environment.py','field_feedback.py'):
        need(sha(before/name)==sha(after/name),'native intervention changed')
    def symbols(path):
        tree=ast.parse(path.read_text());out={}
        for node in tree.body:
            if isinstance(node,(ast.ClassDef,ast.FunctionDef)) and node.name in ('Trial','sampling_for'):out[node.name]=ast.dump(node)
            elif isinstance(node,ast.Assign):
                for t in node.targets:
                    if isinstance(t,ast.Name) and t.id in ('NAMESPACE','ARMS','SEEDS','SAMPLING'):out[t.id]=ast.dump(node.value)
        return out
    need(symbols(before/'feedback_protocol.py')==symbols(after/'feedback_protocol.py'),'frozen trial/sampling changed')
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
    need({g['seed'] for g in a['groups']}=={2900000} and {g['arm'] for g in a['groups']}=={'thinking_off','revision_thinking'},'screen scope differs')
    qualification=json.loads(paths['qualification'].read_text())
    need(qualification.get('source')==SCREEN_SOURCE and qualification.get('native_tests')==18 and qualification.get('assessment_tests')==10,'original qualification required')
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
