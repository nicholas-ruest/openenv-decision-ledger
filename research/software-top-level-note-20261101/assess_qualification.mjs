// Actual pinned MetaHarness; its unknown-program-error classification stays fail-closed.
import {PIN,scoreCell} from '../metaharness-compatibility-20261028/adapter.mjs';
import {createHash} from 'node:crypto';
const need=(ok,message)=>{if(!ok)throw Error(message);};
const arms=['baseline','top_level_only'];
const failures={format:'invalid_json_action',truncation:'completion_truncated',provider:'provider_request_failed',budget:'global_token_budget_exhausted',execution:'environment_step_failed'};
export function assess(a){
 need(a?.kind==='top_level_note_qualification'&&a.scripted===true&&a.live_evidence===false&&a.assigned===8&&a.rows?.length===8&&a.all_assigned_in_denominator===true,'complete scripted qualification only');
 return assessSystem(a,true);
}
export function assessScreen(a){
 need(a?.kind==='top_level_paired_screen_archive'&&a.scripted===false&&a.live_evidence===true&&a.assigned===8&&a.rows?.length===8&&a.all_assigned_in_denominator===true&&a.complete===true&&a.independently_replayed===8&&a.supervision_completed===true&&/^[a-f0-9]{64}$/.test(a.case_audit_sha256),'complete independently replayed original supervised screen required');
 return assessSystem(a,false);
}
function assessSystem(a,scripted){
 const seen=new Set();
 for(const r of a.rows){
  const j=r.job;
  need(r.verified===true&&r.scripted===scripted&&r.live_evidence===!scripted&&j.namespace==='top-level-note-20261101'&&j.phase===(scripted?'qualification':'screen')&&j.task_id==='software_repair-ignore-d3'&&j.seed===(scripted?2560000:3200000)&&arms.includes(j.arm)&&Number.isInteger(j.sample)&&j.sample>=0&&j.sample<4,'original qualification identity');
  const identity=Object.fromEntries(Object.entries(j).filter(([k])=>k!=='attempt_id').sort(([a],[b])=>a.localeCompare(b)));
  need(createHash('sha256').update(JSON.stringify(identity)).digest('hex')===j.attempt_id&&!seen.has(j.attempt_id),'unique original assignment');seen.add(j.attempt_id);
  need(['full','partial','wrong',...Object.keys(failures)].includes(r.category),'original Native outcome class');
  need(Number.isSafeInteger(r.generation_tokens)&&r.generation_tokens>=0&&r.generation_tokens<=6000&&Number.isSafeInteger(r.native_observation_tokens)&&r.native_observation_tokens>=0&&r.completion_with_observations===r.generation_tokens+r.native_observation_tokens&&r.completion_with_observations<=8192,'all observations counted');
  need(r.model_responses===1&&r.controller_actions?.length===0,'one unmodified model action');
  if(['full','partial','wrong'].includes(r.category))need(r.failure_origin==='native_semantic_outcome'&&Number.isFinite(r.semantic_reward)&&r.semantic_reward>=0&&r.semantic_reward<=1&&r.terminal_reward_observed===r.semantic_reward,'observed semantic outcome');
  else need(r.semantic_reward===null,'failure is not a semantic answer');
  if(['full','partial','wrong'].includes(r.category))need(r.category==='full'?r.semantic_reward===1:r.category==='wrong'?r.semantic_reward===0:r.semantic_reward>0&&r.semantic_reward<1,'semantic class mismatch');
  if(r.failure_origin==='model_program_rejection')need(r.category==='execution'&&r.native_compile_rejected===true&&r.terminal_reward_observed===0,'Native program rejection proof');
  if(r.failure_origin==='model_program_runtime_error')need(r.category==='execution'&&r.native_compile_rejected===false&&r.native_runtime_error_observed===true&&r.terminal_reward_observed===0,'Native runtime error proof');
  if(r.category==='execution')need(['model_program_rejection','model_program_runtime_error','native_execution_unverified'].includes(r.failure_origin),'explicit execution origin');
  if(['format','truncation'].includes(r.category))need(r.failure_origin==='model_output_'+r.category,'model output origin');
  if(['provider','budget'].includes(r.category))need(r.failure_origin===r.category+'_failure','provider/budget origin');
 }
 const groups=arms.map(arm=>{
  const rows=a.rows.filter(r=>r.job.arm===arm);need(rows.length===4&&new Set(rows.map(r=>r.job.sample)).size===4,'four original draws');
  const projected=rows.map(r=>({type:'episode',seed:r.job.seed,attempt:r.job.sample,reward:r.semantic_reward??0,
    failure:r.failure_origin.startsWith('model_program_')?'model_program_error':failures[r.category]??null,
    trajectory:{accounting:{generation_tokens:r.generation_tokens},provider_metrics:[{finish_reason:r.finish_reason}]}}));
  const fitness=scoreCell(projected);
  return {arm,assigned:4,mean_semantic:rows.reduce((sum,r)=>sum+(r.semantic_reward??0),0)/4,categories:Object.fromEntries(['full','partial','wrong',...Object.keys(failures)].map(k=>[k,rows.filter(r=>r.category===k).length])),full:rows.filter(r=>r.category==='full').length,model_program_failures:rows.filter(r=>r.failure_origin.startsWith('model_program_')).length,signal:fitness.signal,eligible:fitness.eligible,infra:fitness.infra,reasoning:fitness.reasoning};
 });
 const selected=!scripted&&groups[1].full>groups[0].full&&groups[1].mean_semantic>=groups[0].mean_semantic&&a.rows.every(r=>!['provider','budget'].includes(r.category)&&!(r.category==='execution'&&r.failure_origin==='native_execution_unverified'));
 return {kind:scripted?'top_level_note_qualification_assessment':'top_level_note_screen_assessment',groups,metaharness_source:PIN,actual_module:'fitness.mjs:scoreCell',
  compatibility_limit:'Pinned upstream treats unknown model_program_error as infra. It is retained fail-closed, never projected as reasoning or semantic partial credit.',
  scripted,live_evidence:!scripted,selection_passed:selected,is_training:false,model_improvement:false};
}
