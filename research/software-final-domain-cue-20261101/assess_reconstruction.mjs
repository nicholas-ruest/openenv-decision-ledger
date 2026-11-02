// Read-only archive analysis. Input JSON cannot authenticate provider provenance.
import {PIN,scoreCell} from '../metaharness-compatibility-20261028/adapter.mjs';
import {createHash} from 'node:crypto';
const need=(x,m)=>{if(!x)throw Error(m);};
const arms=['common_review','final_domain_reminder'];
const failures={format:'invalid_json_action',truncation:'completion_truncated',provider:'provider_request_failed',budget:'global_token_budget_exhausted',execution:'environment_step_failed'};
export function assessReconstruction(a){
 need(a?.kind==='case_bound_archive_reconstruction'&&a.replay_only===true&&a.provider_provenance_attested===false&&a.execution_authorized===false&&a.selection_passed===false&&a.model_improvement===false&&a.assigned===8&&a.rows?.length===8&&a.all_assigned_in_denominator===true,'original read-only archive reconstruction required');
 need(/^[a-f0-9]{64}$/.test(a.case_audit_sha256)&&/^[a-f0-9]{40}$/.test(a.source),'source and case receipt identities required');
 const base={kind:'final_domain_cue_reconstruction_assessment',assigned:8,all_assigned_in_denominator:true,replay_only:true,provider_provenance_attested:false,execution_authorized:false,selection_passed:false,confirmation_authorized:false,model_improvement:false,leaderboard_gain:false,is_training:false};
 const order=[];let seed;
 for(let sample=0;sample<4;sample++)for(const arm of sample%2===0?arms:[...arms].reverse())order.push([sample,arm]);
 a.rows.forEach((row,i)=>{
  const j=row.job;need(j&&j.namespace==='final-review-domain-reminder-20261101'&&j.phase==='screen'&&j.task_id==='software_repair-ignore-d3'&&Number.isSafeInteger(j.seed)&&j.seed>=0&&j.sample===order[i][0]&&j.arm===order[i][1],'original ordered screen assignments required');
  seed??=j.seed;need(j.seed===seed,'same case required');
  const identity=Object.fromEntries(Object.entries(j).filter(([k])=>k!=='attempt_id').sort(([a],[b])=>a.localeCompare(b)));
  need(createHash('sha256').update(JSON.stringify(identity)).digest('hex')===j.attempt_id,'original assignment digest');
  need(!('scripted' in row)&&!('live_evidence' in row)&&row.provider_provenance_attested===false,'replay must not promote provenance');
 });
 need(Number.isInteger(a.independently_replayed_terminal_attempts)&&a.independently_replayed_terminal_attempts>=0&&a.independently_replayed_terminal_attempts<=8,'explicit terminal count');
 if(a.all_terminal_attempts_reconstructed!==true){
  need(a.independently_replayed_terminal_attempts<8&&a.phase_reconstruction===null,'incomplete archive cannot carry complete phase');
  return {...base,complete:false,fitness_computed:false,groups:null,unknown_usage_attempts:a.rows.filter(r=>r.unknown_usage===true).length,descriptive_screen_criterion_met:false};
 }
 need(a.independently_replayed_terminal_attempts===8&&a.rows.every(r=>r.recorded===true&&r.verified===true&&r.replay_only===true&&r.unknown_usage!==true),'all eight independent terminal reconstructions required');
 const ids=new Set();
 for(const row of a.rows){
  const j=row.job,identity=Object.fromEntries(Object.entries(j).filter(([k])=>k!=='attempt_id').sort(([a],[b])=>a.localeCompare(b)));
  need(row.verified===true&&j.namespace==='final-review-domain-reminder-20261101'&&j.phase==='screen'&&j.task_id==='software_repair-ignore-d3'&&j.seed===seed&&arms.includes(j.arm)&&Number.isInteger(j.sample)&&j.sample>=0&&j.sample<4,'original screen identity');
  need(createHash('sha256').update(JSON.stringify(identity)).digest('hex')===j.attempt_id&&!ids.has(j.attempt_id),'unique original assignment');ids.add(j.attempt_id);
  need(['full','partial','wrong',...Object.keys(failures)].includes(row.category),'explicit terminal outcome');
  need(Number.isSafeInteger(row.generation_tokens)&&row.generation_tokens>=0&&Number.isSafeInteger(row.native_observation_tokens)&&row.native_observation_tokens>=0&&row.completion_with_observations===row.generation_tokens+row.native_observation_tokens&&row.completion_with_observations<=8192,'all actual observations counted');
  need([1,2].includes(row.model_responses)&&row.controller_actions?.length===0&&row.computed_relation_exposed===false&&row.usable_relation_counterexample_exposed===false,'unmodified original model actions; no computed feedback');
  need(typeof row.final_domain_reminder_presented==='boolean'&&typeof row.final_domain_reminder_exposed==='boolean'&&(!row.final_domain_reminder_presented||j.arm===arms[1])&&row.final_domain_reminder_exposed===(row.final_domain_reminder_presented&&row.model_responses===2),'actual late reminder exposure');
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
  return {arm,assigned:4,full:rows.filter(r=>r.category==='full').length,mean_semantic:rows.reduce((s,r)=>s+(r.semantic_reward??0),0)/4,reminder_exposures:rows.filter(r=>r.final_domain_reminder_exposed).length,signal:fitness.signal,eligible:fitness.eligible,partial:fitness.partial,format:fitness.format,truncation:fitness.truncation,infra:fitness.infra,reasoning:fitness.reasoning,categories:Object.fromEntries(['full','partial','wrong',...Object.keys(failures)].map(k=>[k,rows.filter(r=>r.category===k).length]))};
 });
 const criterion=groups[1].reminder_exposures>0&&groups[1].full>groups[0].full&&groups[1].mean_semantic>=groups[0].mean_semantic&&a.rows.every(r=>!['provider','budget'].includes(r.category)&&!(r.category==='execution'&&r.failure_origin==='native_execution_unverified'));
 return {...base,complete:true,fitness_computed:true,groups,descriptive_screen_criterion_met:criterion,metaharness_source:PIN,actual_module:'fitness.mjs:scoreCell',upstream_confirmation_applied:false,confirmation_limitation:'Repeated same-case draws are not the upstream changed-genome consecutive-seed-block confirmation design.'};
}
