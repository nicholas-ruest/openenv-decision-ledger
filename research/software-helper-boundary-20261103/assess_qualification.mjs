// Qualification only: call actual pinned MIT MetaHarness without live promotion.
import {PIN,scoreCell} from '../metaharness-compatibility-20261028/adapter.mjs';
import {createHash} from 'node:crypto';
const need=(x,m)=>{if(!x)throw Error(m);};
const arms=['common_review','helper_input_boundary'];
const failures={format:'invalid_json_action',truncation:'completion_truncated',provider:'provider_request_failed',budget:'global_token_budget_exhausted',execution:'environment_step_failed'};
export function assess(a){
 need(a?.kind==='helper_input_boundary_qualification'&&a.scripted===true&&a.live_evidence===false&&a.assigned===8&&a.rows?.length===8&&a.all_assigned_in_denominator===true,'complete scripted qualification only');
 const ids=new Set();
 for(const row of a.rows){
  const j=row.job,identity=Object.fromEntries(Object.entries(j).filter(([k])=>k!=='attempt_id').sort(([a],[b])=>a.localeCompare(b)));
  need(row.verified===true&&row.scripted===true&&row.live_evidence===false&&j.namespace==='helper-input-boundary-20261103'&&j.phase==='qualification'&&j.task_id==='software_repair-ignore-d3'&&j.seed===2560000&&arms.includes(j.arm)&&Number.isInteger(j.sample)&&j.sample>=0&&j.sample<4,'original qualification identity');
  need(createHash('sha256').update(JSON.stringify(identity)).digest('hex')===j.attempt_id&&!ids.has(j.attempt_id),'unique original assignment');ids.add(j.attempt_id);
  need(['full','partial','wrong',...Object.keys(failures)].includes(row.category),'explicit terminal outcome');
  need(Number.isSafeInteger(row.generation_tokens)&&row.generation_tokens>=0&&Number.isSafeInteger(row.native_observation_tokens)&&row.native_observation_tokens>=0&&row.completion_with_observations===row.generation_tokens+row.native_observation_tokens&&row.completion_with_observations<=8192,'all actual observations counted');
  need([1,2].includes(row.model_responses)&&row.controller_actions?.length===0&&row.computed_relation_exposed===false&&row.usable_relation_counterexample_exposed===false,'unmodified original model actions; no computed feedback');
  need(typeof row.helper_input_boundary_presented==='boolean'&&typeof row.helper_input_boundary_exposed==='boolean'&&(!row.helper_input_boundary_presented||j.arm===arms[1])&&row.helper_input_boundary_exposed===(row.helper_input_boundary_presented&&row.model_responses===2),'actual helper input-boundary reminder exposure');
  if(['full','partial','wrong'].includes(row.category)){
   need(row.model_responses===2&&row.failure_origin==='native_semantic_outcome'&&row.terminal_reward_observed===row.semantic_reward,'original final Native grade');
   need(row.category==='full'?row.semantic_reward===1:row.category==='wrong'?row.semantic_reward===0:row.semantic_reward>0&&row.semantic_reward<1,'semantic class mismatch');
  }else need(row.semantic_reward===null,'failure cannot become a semantic repair');
  if(['format','truncation'].includes(row.category))need(row.failure_origin==='model_output_'+row.category,'original model output failure');
  if(['provider','budget'].includes(row.category))need(row.failure_origin===row.category+'_failure','original infrastructure/budget failure');
  if(row.category==='execution'){
   need(row.model_responses===2,'original final execution outcome');
   need(['model_program_rejection','model_program_runtime_error','native_execution_unverified'].includes(row.failure_origin),'original execution origin');
   if(row.failure_origin==='model_program_rejection')need(row.native_compile_rejected===true&&row.terminal_reward_observed===0,'original program rejection');
   if(row.failure_origin==='model_program_runtime_error')need(row.native_compile_rejected===false&&row.native_runtime_error_observed===true&&row.terminal_reward_observed===0,'original runtime error');
  }
 }
 const groups=arms.map(arm=>{
  const rows=a.rows.filter(r=>r.job.arm===arm);need(rows.length===4&&new Set(rows.map(r=>r.job.sample)).size===4,'four original draws in denominator');
  const fitness=scoreCell(rows.map(r=>({type:'episode',seed:r.job.seed,attempt:r.job.sample,reward:r.semantic_reward??0,failure:r.failure_origin.startsWith('model_program_')?'model_program_error':failures[r.category]??null,trajectory:{accounting:{generation_tokens:r.generation_tokens},provider_metrics:[{finish_reason:r.finish_reason}]}})));
  return {arm,assigned:4,full:rows.filter(r=>r.category==='full').length,mean_semantic:rows.reduce((s,r)=>s+(r.semantic_reward??0),0)/4,reminder_exposures:rows.filter(r=>r.helper_input_boundary_exposed).length,signal:fitness.signal,eligible:fitness.eligible,infra:fitness.infra,reasoning:fitness.reasoning};
 });
 return {kind:'helper_input_boundary_qualification_assessment',groups,metaharness_source:PIN,actual_module:'fitness.mjs:scoreCell',scripted:true,live_evidence:false,selection_passed:false,model_improvement:false,is_training:false};
}
