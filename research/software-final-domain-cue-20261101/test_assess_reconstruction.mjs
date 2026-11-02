import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {assessReconstruction as assess} from './assess_reconstruction.mjs';
const digest=j=>createHash('sha256').update(JSON.stringify(Object.fromEntries(Object.entries(j).sort(([a],[b])=>a.localeCompare(b))))).digest('hex');
function fixture(){
 const rows=[];
 for(let sample=0;sample<4;sample++)for(const arm of sample%2===0?['common_review','final_domain_reminder']:['final_domain_reminder','common_review']){
  const j={namespace:'final-review-domain-reminder-20261101',phase:'screen',task_id:'software_repair-ignore-d3',seed:1,sample,arm};
  const full=arm==='final_domain_reminder'||sample<2;
  rows.push({job:{...j,attempt_id:digest(j)},verified:true,recorded:true,replay_only:true,provider_provenance_attested:false,category:full?'full':'wrong',failure_origin:'native_semantic_outcome',semantic_reward:full?1:0,terminal_reward_observed:full?1:0,generation_tokens:100,native_observation_tokens:20,completion_with_observations:120,model_responses:2,controller_actions:[],computed_relation_exposed:false,usable_relation_counterexample_exposed:false,final_domain_reminder_presented:arm==='final_domain_reminder',final_domain_reminder_exposed:arm==='final_domain_reminder',finish_reason:'stop'});
 }
 return {kind:'case_bound_archive_reconstruction',rows,assigned:8,all_assigned_in_denominator:true,independently_replayed_terminal_attempts:8,all_terminal_attempts_reconstructed:true,phase_reconstruction:{},case_audit_sha256:'a'.repeat(64),source:'b'.repeat(40),replay_only:true,provider_provenance_attested:false,execution_authorized:false,selection_passed:false,model_improvement:false};
}
test('actual pinned scoreCell; descriptive advantage never grants authority',()=>{
 const a=assess(fixture());assert.equal(a.actual_module,'fitness.mjs:scoreCell');assert.equal(a.metaharness_source,'b8c3d38de41203faf633ef6dceb8452a4727b0ea');assert.deepEqual(a.groups.map(g=>g.full),[2,4]);assert.equal(a.descriptive_screen_criterion_met,true);assert.equal(a.groups[0].signal,1);assert.equal(a.groups[1].signal,0);
 for(const k of ['selection_passed','confirmation_authorized','execution_authorized','model_improvement','provider_provenance_attested','is_training'])assert.equal(a[k],false);
});
test('partial Native semantics preserved separately from full solves',()=>{const f=fixture(),r=f.rows[0];Object.assign(r,{category:'partial',semantic_reward:.5,terminal_reward_observed:.5});const a=assess(f);assert.equal(a.groups[0].partial,1);assert.equal(a.groups[0].full,1);assert.equal(a.groups[0].mean_semantic,.375);});
test('incomplete prefix retains denominator and unknown usage without fitness',()=>{const f=fixture();Object.assign(f,{all_terminal_attempts_reconstructed:false,independently_replayed_terminal_attempts:7,phase_reconstruction:null});Object.assign(f.rows[0],{recorded:false,verified:false,unknown_usage:true,generation_tokens:null,semantic_reward:null,category:'provider'});const a=assess(f);assert.equal(a.assigned,8);assert.equal(a.unknown_usage_attempts,1);assert.equal(a.groups,null);assert.equal(a.fitness_computed,false);assert.equal(a.descriptive_screen_criterion_met,false);});
test('no qualification relabeling, live assertion or confirmation inputs',()=>{for(const edit of [f=>f.kind='final_domain_cue_qualification',f=>f.provider_provenance_attested=true,f=>f.rows[0].scripted=true,f=>f.rows[0].live_evidence=true,f=>f.rows[0].job.phase='confirmation']){const f=fixture();edit(f);assert.throws(()=>assess(f));}});
test('reject changed assignment, case, duplicate, missing or reordered draws',()=>{for(const edit of [f=>f.rows.pop(),f=>f.rows.reverse(),f=>f.rows[1]=f.rows[0],f=>f.rows[0].job.seed++,f=>f.rows[0].job.sample=true,f=>f.source='bad']){const f=fixture();edit(f);assert.throws(()=>assess(f));}});
test('strict actual token and reminder-exposure guards',()=>{for(const edit of [r=>r.generation_tokens=null,r=>r.completion_with_observations=8193,r=>r.controller_actions=['edit'],r=>r.final_domain_reminder_exposed=true,r=>r.computed_relation_exposed=true]){const f=fixture();edit(f.rows[0]);assert.throws(()=>assess(f));}});
test('program error stays nonsemantic, upstream fails closed to infra',()=>{const f=fixture();Object.assign(f.rows[0],{category:'execution',semantic_reward:null,terminal_reward_observed:0,failure_origin:'model_program_runtime_error',native_compile_rejected:false,native_runtime_error_observed:true});const a=assess(f);assert.equal(a.groups[0].infra,1);assert.equal(a.groups[0].eligible,3);assert.equal(a.groups[0].categories.execution,1);});
test('incomplete archive cannot smuggle complete phase or terminal credit',()=>{const f=fixture();f.all_terminal_attempts_reconstructed=false;assert.throws(()=>assess(f));const g=fixture();g.rows[0].terminal_reward_observed=1;g.rows[0].semantic_reward=0;assert.throws(()=>assess(g));});
