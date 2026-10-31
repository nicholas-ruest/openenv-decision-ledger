import {createHash} from 'node:crypto';
// Actual pinned MIT MetaHarness fitness over qualification system outcomes.
import {PIN,scoreCell} from '../metaharness-compatibility-20261028/adapter.mjs';
const need=(x,m)=>{if(!x)throw Error(m);};
const arms=['standard_revision','preserve_declared_helpers'];
const failure={format:'invalid_json_action',provider:'provider_request_failed',execution:'environment_step_failed',budget:'global_token_budget_exhausted',truncation:'completion_truncated'};
export function assess(a){
 need(a?.scripted===true&&a.live_evidence===false&&a.kind==='qualification_phase_assembly','qualification only; no live admission');
 return assessSystem(a,'qualification',3100000);
}
export function assessScreen(a){
 need(a?.scripted===false&&a.live_evidence===true&&a.kind==='screen_phase_assembly'&&/^[a-f0-9]{64}$/.test(a.case_audit_sha256),'independently replayed sealed screen only');
 return assessSystem(a,'screen',3140000);
}
function assessSystem(a,phase,seed){
 need(a.assigned===8&&a.rows?.length===8&&a.assigned_jobs?.length===8&&a.all_assigned_in_denominator===true,'all eight assignments required');
 const ids=new Set();
 for(let i=0;i<8;i++){
  const r=a.rows[i],j=a.assigned_jobs[i];
  need(r.job&&Object.keys(r.job).length===Object.keys(j).length&&Object.keys(j).every(k=>r.job[k]===j[k])&&!ids.has(j.attempt_id),'original unique assignment required');ids.add(j.attempt_id);
  need(j.namespace==='declared-helper-controller-20261031'&&j.task_id==='software_repair-ignore-d2'&&j.phase===phase&&j.seed===seed&&arms.includes(j.arm)&&Number.isInteger(j.sample)&&j.sample>=0&&j.sample<4,'exact assigned case required');
  const identity=Object.fromEntries(Object.entries(j).filter(([k])=>k!=='attempt_id').sort(([a],[b])=>a.localeCompare(b)));
  need(createHash('sha256').update(JSON.stringify(identity)).digest('hex')===j.attempt_id,'original assignment digest required');
  need(['full','partial','wrong',...Object.keys(failure),'unexecuted'].includes(r.category),'explicit outcome class required');
  need(Array.isArray(r.controller_actions),'explicit controller provenance required');
  if(j.arm===arms[0])need(r.controller_actions.length===0,'baseline cannot have controller edits');
  for(const action of r.controller_actions)need(action.authored_by==='controller'&&action.kind==='preserve_declared_helpers'&&action.generated_tokens===0,'controller edits are not model responses');
  if(r.replayed){
   need(Number.isSafeInteger(r.generation_tokens)&&r.generation_tokens>=0,'no invented generation cost');
   need(['native_observation_tokens','controller_observation_tokens'].every(k=>Number.isSafeInteger(r[k])&&r[k]>=0)
     &&r.completion_with_observations===r.generation_tokens+r.native_observation_tokens+r.controller_observation_tokens
     &&r.completion_with_observations<=8192,'all Native/controller observations consume the original budget');
   need(Number.isSafeInteger(r.model_responses)&&r.model_responses>=1&&r.model_responses<=2,'two original model responses only');
   if(r.category==='full')need(r.semantic_reward===1,'full/native mismatch');
   else if(r.category==='wrong')need(r.semantic_reward===0,'wrong/native mismatch');
   else if(r.category==='partial')need(Number.isFinite(r.semantic_reward)&&r.semantic_reward>0&&r.semantic_reward<1,'partial/native mismatch');
   else need(r.semantic_reward===null,'failures cannot be model solves');
   if(['full','partial','wrong'].includes(r.category))need(r.terminal_reward_observed===r.semantic_reward,'terminal Native reward differs');
  }
 }
 const complete=a.complete===true&&a.rows.every(r=>r.recorded&&r.replayed)&&a.independently_replayed===8;
 const groups=arms.map(arm=>{
  const rs=a.rows.filter(r=>r.job.arm===arm);need(rs.length===4&&new Set(rs.map(r=>r.job.sample)).size===4,'four distinct assigned samples per arm');
  const projected=complete?rs.map(r=>({type:'episode',seed:r.job.seed,attempt:r.job.sample,reward:r.semantic_reward??0,
    failure:failure[r.category]??null,trajectory:{accounting:{generation_tokens:r.generation_tokens},provider_metrics:[{finish_reason:r.finish_reason}]}})):null;
  const score=projected?scoreCell(projected):null;
  return {arm,assigned:4,recorded:rs.filter(r=>r.recorded).length,
    categories:Object.fromEntries(['full','partial','wrong',...Object.keys(failure),'unexecuted'].map(k=>[k,rs.filter(r=>r.category===k).length])),
    controller_assisted_full:rs.filter(r=>r.category==='full'&&r.controller_actions.length>0).length,
    model_response_only_full:rs.filter(r=>r.category==='full'&&!r.controller_actions.length).length,
    metaharness:score?{signal:score.signal,eligible:score.eligible,solved:score.solved,partial:score.partial,truncation:score.truncation,infra:score.infra}:null};
 });
 const live=phase==='screen';
 const success=complete&&groups[1].categories.full>groups[0].categories.full
   &&a.rows.filter(r=>r.job.arm===arms[1]).reduce((s,r)=>s+(r.semantic_reward??0),0)>=a.rows.filter(r=>r.job.arm===arms[0]).reduce((s,r)=>s+(r.semantic_reward??0),0)
   &&a.rows.every(r=>!['provider','budget','execution','unexecuted'].includes(r.category));
 return {kind:phase+'_system_outcome_assessment',assigned:8,groups,complete,
   metaharness_source:PIN,actual_module:complete?'fitness.mjs:scoreCell':null,
   metaharness_suppressed_reason:complete?null:'incomplete_or_unreplayed_assignments',
   outcome_scope:live?'model_plus_controller_system_attempts':'scripted_model_plus_controller_system_controls',live_evidence:live,
   case_audit_sha256:live?a.case_audit_sha256:null,
   is_training:false,selection_passed:live&&success,promotion:false,model_improvement:false,leaderboard_gain:false};
}
