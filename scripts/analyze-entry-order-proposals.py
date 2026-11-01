"""Posthoc investigator replay of already closed original proposals; no provider."""
from pathlib import Path
import argparse,ast,json,sys
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--archive',required=True,type=Path)
out=parser.parse_args().archive.resolve()
closed=json.loads((out/'closed-independent-verification.json').read_text())
assert closed['supervisor']['shutdown_verified'] is True
sys.path.insert(0,str(out/'source/research/software-entry-order-review-20261101'))
import finite_caller as c,guarded_transport as b,entry_case as lease
from repair_env.environment import RepairAction,check
from repair_env.runner import Program,Rejected
from repair_env.tasks import SOURCE_PATH
meta=json.loads((out/'execution-source.json').read_text()); b.verify_clean_source(meta['source']);b.verify_dependencies()
proof=Path(meta['case_audit_path']); expected=meta['case_audit_sha256']
def functions(code):
 try:return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(code).body if isinstance(n,ast.FunctionDef)}
 except SyntaxError:return None
rows=[]
for job in c.p.jobs('screen'):
 folder=out/'screen'/job['attempt_id']; f=folder/'response-0.json'
 row=dict(arm=job['arm'],sample=job['sample'],first_proposal_known=f.exists(),posthoc_not_model_solve=True)
 if f.exists():
  response=json.loads(f.read_text()); trial=lease.materialize(job,proof,expected)
  first=trial.consume(response['choices'][0]['message'],response['choices'][0].get('finish_reason'))
  if first['category']=='awaiting_revision' and not trial.env._write_error:
   code=trial.env._direct._files[SOURCE_PATH]
   supplied=functions(trial.env._direct._task.initial_source);supplied={k:v for k,v in supplied.items() if k!=trial.env._direct._task.entrypoint}
   first_funcs=functions(code)
   row['supplied_helpers_preserved_in_first']=first_funcs is not None and all(first_funcs.get(k)==v for k,v in supplied.items())
   diagnostic=c.p.d.diagnose(trial.env._visible,code)
   row.update(initial_relation_available=diagnostic['kind']=='public_entry_order_relation',initial_order_sensitive_examples=diagnostic.get('order_sensitive_examples'))
   grade=trial.env._direct._core.step(RepairAction(op='submit')).model_dump()
   grade['error']=trial.env._write_error or grade['error']
   result=c.p.classify(trial.env,grade)
   row.update(posthoc_first_category=result['category'],posthoc_first_semantic_reward=result['semantic_reward'])
   second=folder/'response-1.json'
   if second.exists():
    last=json.loads(second.read_text())
    try:
     action=c.p.DirectRepairAction.model_validate_json(last['choices'][0]['message'].get('content'),strict=True)
     final_code=action.content or code
     old,new=functions(code),functions(final_code)
     diagnostic=c.p.d.diagnose(trial.env._visible,final_code)
     row.update(final_relation_available=diagnostic['kind']=='public_entry_order_relation',final_order_sensitive_examples=diagnostic.get('order_sensitive_examples'),supplied_helpers_preserved_in_final=new is not None and all(new.get(k)==v for k,v in supplied.items()))
     try:row['final_supplied_examples_passed']=check(Program(final_code),trial.env._direct._task,trial.env._direct._task.public)[0]
     except (Rejected,RecursionError):row['final_supplied_examples_passed']=None
     row.update(final_module_identical=final_code==code,first_functions_preserved=(old is not None and new is not None and all(new.get(k)==v for k,v in old.items())),changed_first_functions=sum(new.get(k)!=v for k,v in old.items()) if old is not None and new is not None else None)
    except (ValueError,TypeError):row['final_action_invalid']=True
  elif first['category']=='awaiting_revision':row.update(first_write_rejected=True,posthoc_first_category='execution',posthoc_first_semantic_reward=None,initial_relation_available=False)
  else:row['first_protocol_category']=first['category']
 record=folder/'record.json'
 if record.exists():
  value=json.loads(record.read_text());row.update(original_final_category=value['category'],original_final_semantic_reward=value['semantic_reward'],original_computed_relation_exposed=value.get('computed_relation_exposed',False),original_usable_counterexample_exposed=value.get('usable_relation_counterexample_exposed',False))
 rows.append(row)
result=dict(kind='entry_order_closed_posthoc_first_proposal_diagnosis',posthoc_investigator_control=True,not_new_model_outcomes=True,original_archive_unchanged=True,new_model_calls=0,new_cases=0,rows=rows)
with (out/'closed-posthoc-proposal-diagnosis.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
