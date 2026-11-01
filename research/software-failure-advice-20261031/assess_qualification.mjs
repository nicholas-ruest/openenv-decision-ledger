// Scripted qualification only. Actual pinned MIT MetaHarness, no live gate.
import {createHash} from 'node:crypto';
import {PIN,scoreCell} from '../metaharness-compatibility-20261028/adapter.mjs';
const need=(ok,message)=>{if(!ok)throw Error(message);};
const failures={format:'invalid_json_action',provider:'provider_request_failed',execution:'environment_step_failed',budget:'global_token_budget_exhausted',truncation:'completion_truncated'};
const arms=['standard_revision','focused_failure_advice'];
export function assess(a){
 need(a?.kind==='failure_advice_qualification'&&a.scripted===true&&a.live_evidence===false,'scripted qualification only');
 return assessSystem(a,'qualification',3100000,true);
}
export function assessScreen(a){
 need(a?.kind==='screen_phase_assembly'&&a.scripted===false&&a.live_evidence===true&&a.complete===true&&a.independently_replayed===8&&/^[a-f0-9]{64}$/.test(a.case_audit_sha256),'complete independently replayed sealed screen required');
 return assessSystem(a,'screen',3160000,false);
}
function assessSystem(a,phase,seed,scripted){
 need(a.assigned===8&&a.rows?.length===8&&a.all_assigned_in_denominator===true,'all eight original assignments required');
 const ids=new Set();
 for(const r of a.rows){
  const j=r.job;
  need(r.verified===true&&r.scripted===scripted&&r.live_evidence===!scripted,'independently replayed qualification required');
  need(j.namespace==='public-failure-advice-20261031'&&j.phase===phase&&j.task_id==='software_repair-ignore-d2'&&j.seed===seed&&arms.includes(j.arm)&&Number.isInteger(j.sample)&&j.sample>=0&&j.sample<4,'exact qualification case and arm required');
  const identity=Object.fromEntries(Object.entries(j).filter(([k])=>k!=='attempt_id').sort(([a],[b])=>a.localeCompare(b)));
  need(createHash('sha256').update(JSON.stringify(identity)).digest('hex')===j.attempt_id&&!ids.has(j.attempt_id),'unique original assignment digest');ids.add(j.attempt_id);
  need(['full','partial','wrong',...Object.keys(failures)].includes(r.category),'explicit outcome class');
  need(['generation_tokens','native_observation_tokens','advice_observation_tokens'].every(k=>Number.isSafeInteger(r[k])&&r[k]>=0)&&r.completion_with_observations===r.generation_tokens+r.native_observation_tokens+r.advice_observation_tokens&&r.completion_with_observations<=8192,'all observations counted within original allowance');
  need(Number.isInteger(r.model_responses)&&r.model_responses>=1&&r.model_responses<=2&&Number.isInteger(r.advice_deliveries)&&r.advice_deliveries>=0&&r.advice_deliveries<=1,'finite original response and advice schedule');
  if(j.arm===arms[0])need(r.advice_deliveries===0&&r.advice_observation_tokens===0,'baseline advice contamination');
  need((r.advice_deliveries===0)===(r.advice_observation_tokens===0),'advice exposure and accounting disagree');
  if(['full','partial','wrong'].includes(r.category)){
   need(Number.isFinite(r.semantic_reward)&&r.semantic_reward>=0&&r.semantic_reward<=1&&r.terminal_reward_observed===r.semantic_reward,'Native terminal reward required');
   need(r.category==='full'?r.semantic_reward===1:r.category==='wrong'?r.semantic_reward===0:r.semantic_reward>0&&r.semantic_reward<1,'semantic class mismatch');
  }else need(r.semantic_reward===null,'failure is not a semantic solve');
 }
 const groups=arms.map(arm=>{
  const rows=a.rows.filter(r=>r.job.arm===arm);need(rows.length===4&&new Set(rows.map(r=>r.job.sample)).size===4,'four original samples per arm');
  const score=scoreCell(rows.map(r=>({type:'episode',seed:r.job.seed,attempt:r.job.sample,reward:r.semantic_reward??0,failure:failures[r.category]??null,trajectory:{accounting:{generation_tokens:r.generation_tokens},provider_metrics:[{finish_reason:r.finish_reason}]}})));
  return {arm,assigned:4,full:rows.filter(r=>r.category==='full').length,mean_semantic:rows.reduce((n,r)=>n+(r.semantic_reward??0),0)/4,categories:Object.fromEntries(['full','partial','wrong',...Object.keys(failures)].map(k=>[k,rows.filter(r=>r.category===k).length])),advice_deliveries:rows.reduce((n,r)=>n+r.advice_deliveries,0),signal:score.signal,eligible:score.eligible,solved:score.solved,partial:score.partial,truncation:score.truncation,infra:score.infra};
 });
 const selected=!scripted&&groups[1].advice_deliveries>0&&groups[1].full>groups[0].full&&groups[1].mean_semantic>=groups[0].mean_semantic&&a.rows.every(r=>!['provider','budget','execution'].includes(r.category));
 return {kind:'failure_advice_'+phase+'_assessment',groups,metaharness_source:PIN,actual_module:'fitness.mjs:scoreCell',scripted,live_evidence:!scripted,case_audit_sha256:scripted?null:a.case_audit_sha256,selection_passed:selected,promotion:false,is_training:false,model_improvement:false,leaderboard_gain:false};
}
