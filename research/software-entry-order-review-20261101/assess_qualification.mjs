// Actual pinned MetaHarness on complete scripted qualification evidence only.
import {createHash} from 'node:crypto';
import {PIN,scoreCell} from '../metaharness-compatibility-20261028/adapter.mjs';
const need=(ok,message)=>{if(!ok)throw Error(message);};
const arms=['relation_only','computed_relation'];
const failures={format:'invalid_json_action',truncation:'completion_truncated',provider:'provider_request_failed',budget:'global_token_budget_exhausted',execution:'environment_step_failed'};
export function assess(a){
 need(a?.kind==='entry_order_review_qualification'&&a.scripted===true&&a.live_evidence===false&&a.assigned===8&&a.rows?.length===8&&a.all_assigned_in_denominator===true,'complete scripted qualification required');
 const ids=new Set();
 for(const r of a.rows){
  const j=r.job;
  need(r.verified===true&&r.scripted===true&&r.live_evidence===false&&j.namespace==='public-entry-order-review-20261101'&&j.phase==='qualification'&&j.task_id==='software_repair-ignore-d3'&&j.seed===2560000&&arms.includes(j.arm)&&Number.isInteger(j.sample)&&j.sample>=0&&j.sample<4,'original qualification identity');
  const identity=Object.fromEntries(Object.entries(j).filter(([k])=>k!=='attempt_id').sort(([a],[b])=>a.localeCompare(b)));
  need(createHash('sha256').update(JSON.stringify(identity)).digest('hex')===j.attempt_id&&!ids.has(j.attempt_id),'unique original assignment');ids.add(j.attempt_id);
  need(['full','partial','wrong',...Object.keys(failures)].includes(r.category),'explicit terminal class');
  need(Number.isSafeInteger(r.generation_tokens)&&r.generation_tokens>=0&&Number.isSafeInteger(r.native_observation_tokens)&&r.native_observation_tokens>=0&&r.completion_with_observations===r.generation_tokens+r.native_observation_tokens&&r.completion_with_observations<=8192,'all actual review and terminal observations counted');
  need([1,2].includes(r.model_responses)&&r.controller_actions?.length===0,'at most two unmodified model actions');
  need(typeof r.computed_relation_exposed==='boolean'&&typeof r.usable_relation_counterexample_exposed==='boolean'&&(!r.usable_relation_counterexample_exposed||r.computed_relation_exposed)&&(!r.computed_relation_exposed||j.arm==='computed_relation'),'original computed-feedback exposure');
  if(['full','partial','wrong'].includes(r.category)){
   need(r.model_responses===2&&r.failure_origin==='native_semantic_outcome'&&r.terminal_reward_observed===r.semantic_reward,'original final Native reward');
   need(r.category==='full'?r.semantic_reward===1:r.category==='wrong'?r.semantic_reward===0:r.semantic_reward>0&&r.semantic_reward<1,'semantic class mismatch');
  }else need(r.semantic_reward===null,'failures cannot become semantic repairs');
  need(!r.computed_relation_exposed||r.model_responses===2,'review exposure requires the original second response');
  if(['format','truncation'].includes(r.category))need(r.failure_origin==='model_output_'+r.category,'original model output failure origin');
  if(['provider','budget'].includes(r.category))need(r.failure_origin===r.category+'_failure','original infrastructure/budget origin');
  if(r.category==='execution')need(r.model_responses===2&&['model_program_rejection','model_program_runtime_error','native_execution_unverified'].includes(r.failure_origin),'original Native execution origin');
  if(r.failure_origin==='model_program_rejection')need(r.category==='execution'&&r.native_compile_rejected===true&&r.terminal_reward_observed===0,'original program rejection');
  if(r.failure_origin==='model_program_runtime_error')need(r.category==='execution'&&r.native_compile_rejected===false&&r.native_runtime_error_observed===true&&r.terminal_reward_observed===0,'original program runtime failure');
 }
 const groups=arms.map(arm=>{
  const rows=a.rows.filter(r=>r.job.arm===arm);need(rows.length===4&&new Set(rows.map(r=>r.job.sample)).size===4,'four original draws');
  const fitness=scoreCell(rows.map(r=>({type:'episode',seed:r.job.seed,attempt:r.job.sample,reward:r.semantic_reward??0,failure:r.failure_origin.startsWith('model_program_')?'model_program_error':failures[r.category]??null,trajectory:{accounting:{generation_tokens:r.generation_tokens},provider_metrics:[{finish_reason:r.finish_reason}]}})));
  return {arm,assigned:4,full:rows.filter(r=>r.category==='full').length,computed_relation_exposures:rows.filter(r=>r.computed_relation_exposed).length,usable_counterexample_exposures:rows.filter(r=>r.usable_relation_counterexample_exposed).length,signal:fitness.signal,eligible:fitness.eligible,infra:fitness.infra,reasoning:fitness.reasoning};
 });
 return {kind:'entry_order_review_qualification_assessment',groups,metaharness_source:PIN,actual_module:'fitness.mjs:scoreCell',scripted:true,live_evidence:false,selection_passed:false,is_training:false,model_improvement:false,leaderboard_gain:false};
}
