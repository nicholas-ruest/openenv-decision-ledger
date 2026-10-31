"""Read-only descriptive summary of existing public reviews; no provider or hidden grades."""
from pathlib import Path
import sys,json
r=Path(sys.argv[1]);rows=[]
for i in range(4):
 path=r/('chunk'+str(i))
 if not path.exists():continue
 for file in path.glob('*.trace.json'):
  trace=json.loads(file.read_text());first=trace['events'][0];last=trace['events'][-1];feedback=None
  for obs in first['native_observations']:
   raw=obs.get('feedback')
   try:value=json.loads(raw) if isinstance(raw,str) else raw
   except (ValueError,TypeError):continue
   if isinstance(value,dict) and value.get('kind')=='public_field_check':
    assert value.get('public_only') is True and value.get('hidden_access') is False
    feedback=value
  row=dict(arm=trace['job']['arm'],sample=trace['job']['sample'],category=trace['record']['category'],first_finish=first['response']['choices'][0]['finish_reason'],first_generation_tokens=first['response']['usage']['completion_tokens'],model_responses=len(trace['events']),revision_limit=trace['events'][1]['requested_max_tokens'] if len(trace['events'])==2 else None,last_finish=last['response']['choices'][0]['finish_reason'],native_observation_tokens=trace['record']['native_observation_tokens'],controller_observation_tokens=trace['record']['controller_observation_tokens'],controller_actions=len(trace['record']['controller_actions']),public_passed=feedback['passed'] if feedback else None,public_total=feedback['total'] if feedback else None,public_execution_errors=feedback['execution_errors'] if feedback else None,mismatch_kinds={})
  if feedback:
   for mismatch in feedback.get('field_mismatches',[]):row['mismatch_kinds'][mismatch['kind']]=row['mismatch_kinds'].get(mismatch['kind'],0)+1
  rows.append(row)
if len(rows)!=8 or len({(x['arm'],x['sample']) for x in rows})!=8:
 raise ValueError('all eight original completed traces required for this descriptive summary')
value=dict(kind='descriptive_public_first_proposal_diagnosis',rows=sorted(rows,key=lambda x:(x['sample'],x['arm'])),hidden_terminal_grades_requested=False,counterfactual_replayed=False,interpretation='Public feedback after each assigned arm; different stochastic draws, not paired counterfactual proposals. Endpoint comparison uses complete original system attempts.')
out=Path(sys.argv[2])
with out.open('x') as f:json.dump(value,f,indent=2)
print(json.dumps(value))
