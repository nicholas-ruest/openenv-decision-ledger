// Actual pinned MetaHarness fitness on scripted qualification only; no live gate.
import {createHash} from 'node:crypto';
import {PIN, scoreCell} from '../metaharness-compatibility-20261028/adapter.mjs';
const need=(ok,message)=>{if(!ok)throw Error(message);};
const arms=['baseline','preserve_supplied'];
const failures={format:'invalid_json_action',provider:'provider_request_failed',execution:'environment_step_failed',budget:'global_token_budget_exhausted',truncation:'completion_truncated'};
export function assess(a){
 need(a?.kind==='preserve_first_qualification'&&a.scripted===true&&a.live_evidence===false,'qualification only');
 need(a.assigned===8&&a.rows?.length===8&&a.all_assigned_in_denominator===true,'complete original denominator');
 const identities=new Set();
 for(const r of a.rows){
  const j=r.job;
  need(r.verified===true&&r.scripted===true&&r.live_evidence===false,'independent qualification replay required');
  need(j.namespace==='preserve-first-action-20261101'&&j.phase==='qualification'&&j.seed===2560000&&j.task_id==='software_repair-ignore-d3'&&arms.includes(j.arm)&&Number.isInteger(j.sample)&&j.sample>=0&&j.sample<4,'exact qualification identity');
  const identity=Object.fromEntries(Object.entries(j).filter(([k])=>k!=='attempt_id').sort(([a],[b])=>a.localeCompare(b)));
  need(createHash('sha256').update(JSON.stringify(identity)).digest('hex')===j.attempt_id&&!identities.has(j.attempt_id),'unique assignment digest');identities.add(j.attempt_id);
  need(['full','partial','wrong',...Object.keys(failures)].includes(r.category),'explicit failure classification');
  need(Number.isSafeInteger(r.generation_tokens)&&r.generation_tokens>=0&&r.generation_tokens<=6000&&Number.isSafeInteger(r.native_observation_tokens)&&r.native_observation_tokens>=0&&r.completion_with_observations===r.generation_tokens+r.native_observation_tokens&&r.completion_with_observations<=8192,'actual observation accounting');
  need(r.model_responses===1&&Array.isArray(r.controller_actions)&&r.controller_actions.length===0,'one unchanged model response');
  if(['full','partial','wrong'].includes(r.category)){
   need(Number.isFinite(r.semantic_reward)&&r.semantic_reward>=0&&r.semantic_reward<=1&&r.terminal_reward_observed===r.semantic_reward,'terminal Native reward');
   need(r.category==='full'?r.semantic_reward===1:r.category==='wrong'?r.semantic_reward===0:r.semantic_reward>0&&r.semantic_reward<1,'semantic class mismatch');
  }else need(r.semantic_reward===null,'failure is not a semantic solve');
 }
 const groups=arms.map(arm=>{
  const rows=a.rows.filter(r=>r.job.arm===arm);need(rows.length===4&&new Set(rows.map(r=>r.job.sample)).size===4,'four original draws per arm');
  const fitness=scoreCell(rows.map(r=>({type:'episode',seed:r.job.seed,attempt:r.job.sample,reward:r.semantic_reward??0,failure:failures[r.category]??null,trajectory:{accounting:{generation_tokens:r.generation_tokens},provider_metrics:[{finish_reason:r.finish_reason}]}})));
  return {arm,assigned:4,full:rows.filter(r=>r.category==='full').length,categories:Object.fromEntries(['full','partial','wrong',...Object.keys(failures)].map(k=>[k,rows.filter(r=>r.category===k).length])),signal:fitness.signal,eligible:fitness.eligible,solved:fitness.solved,partial:fitness.partial,truncation:fitness.truncation,infra:fitness.infra};
 });
 return {kind:'preserve_first_qualification_assessment',groups,metaharness_source:PIN,actual_module:'fitness.mjs:scoreCell',scripted:true,live_evidence:false,selection_passed:false,is_training:false,model_improvement:false,leaderboard_gain:false};
}
