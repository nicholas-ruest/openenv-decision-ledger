import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {assess,project} from './assess.mjs';
const hash=x=>createHash('sha256').update(x).digest('hex');
const arms=['review_control','public_check'];
function fixture(rewards=[0,.25,.75,1]){
  const bundle={namespace:'fictional-test-only',confirmation_observations_materialized:false,screen_jobs:[],screen_groups:[]},rows=[];
  for(const task of ['software_repair-ignore-d3'])for(const seed of [2680000]){
    const problem_sha256=hash(task+seed),group={task_id:task,seed,problem_sha256,arms:{}};
    for(const arm of arms){
      const prompt_sha256=hash(task+seed);group.arms[arm]={prompt_sha256};
      for(let sample=0;sample<4;sample++){
        const job={namespace:'fictional-test-only',phase:'screen',task_id:task,seed,sample,arm,attempt_id:hash(task+seed+sample+arm)};
        bundle.screen_jobs.push(job);
        const r=rewards[sample];
        rows.push({...job,problem_sha256,prompt_sha256,category:r===1?'full':r===0?'wrong':'partial',semantic_reward:r,
          terminal_reward_observed:r,generation_tokens:10,finish_reason:'stop',
          call_id:'fictional-call-'+job.attempt_id,response_id:'fictional-response-'+job.attempt_id,reservation_label:'fictional-reservation-'+job.attempt_id});
      }
    }
    bundle.screen_groups.push(group);
  }
  return {bundle,rows};
}
test('valid partials retain actual rewards and contribute to same-prompt MetaHarness signal',()=>{
  const {bundle,rows}=fixture();const before=structuredClone(rows);const result=assess(bundle,rows);
  assert.equal(result.groups.length,2);
  for(const g of result.groups){assert.equal(g.metaharness.partial,2);assert.equal(g.metaharness.signal,1);}
  assert.equal(result.full_rate_delta,0);assert.equal(result.semantic_mean_delta,0);
  assert.deepEqual(rows,before);assert.equal(result.model_improvement_claim,false);
});
test('failure precedence suppresses native grade one without modifying raw records',()=>{
  const {bundle,rows}=fixture();const row=rows[3];
  Object.assign(row,{category:'budget',semantic_reward:null,terminal_reward_observed:1,call_id:null,response_id:null});
  assert.equal(project(row).reward,0);const result=assess(bundle,rows);
  const group=result.groups.find(g=>g.arm===row.arm&&g.task_id===row.task_id&&g.seed===row.seed);
  assert.equal(group.full,0);assert.equal(group.metaharness.infra,1);assert.equal(group.metaharness.signal,0);
  assert.equal(result.attempts_per_arm,4);assert.equal(row.terminal_reward_observed,1);
});
test('unknown format termination stays unknown; edit rejection is separate in native breakdown',()=>{
  const {bundle,rows}=fixture();Object.assign(rows[0],{category:'format',semantic_reward:null,terminal_reward_observed:null,finish_reason:null});
  Object.assign(rows[1],{category:'edit_rejection',semantic_reward:null,terminal_reward_observed:0});
  const g=assess(bundle,rows).groups[0];
  assert.equal(g.metaharness.truncation,1);assert.equal(g.metaharness.format,1);
  assert.equal(g.native_categories.format,1);assert.equal(g.native_categories.edit_rejection,1);
});
test('between-arm differences never manufacture within-prompt productivity',()=>{
  const {bundle,rows}=fixture([.5,.5,.5,.5]);
  for(const row of rows)if(row.arm===arms[1]){row.semantic_reward=.75;row.terminal_reward_observed=.75;}
  assert.ok(assess(bundle,rows).groups.every(g=>g.metaharness.signal===0));
});
test('paired deltas retain every failure in the original assigned denominator',()=>{
  const {bundle,rows}=fixture([0,0,0,0]);
  for(const row of rows)if(row.arm===arms[1]){
    if(row.sample<2)Object.assign(row,{category:'full',semantic_reward:1,terminal_reward_observed:1});
    else Object.assign(row,{category:'provider',semantic_reward:null,terminal_reward_observed:null,response_id:null});
  }
  const r=assess(bundle,rows);assert.equal(r.full_rate_delta,.5);assert.equal(r.semantic_mean_delta,.5);
  assert.ok(r.pairs.every(p=>p.full_rate_delta===.5));assert.equal(r.procedural_seeds,1);
});
test('incomplete, duplicated, misbound, reused, and contradictory records fail closed',()=>{
  for(const mutate of [
    x=>x.rows.pop(),x=>x.rows[1]=x.rows[0],
    x=>x.rows[0].seed++,x=>x.rows[0].prompt_sha256=hash('changed'),
    x=>x.rows[1].call_id=x.rows[0].call_id,
    x=>x.rows[0].semantic_reward=1,x=>x.rows[0].generation_tokens=NaN,
    x=>x.bundle.screen_jobs[1].sample=0,
  ]){const x=fixture();mutate(x);assert.throws(()=>assess(x.bundle,x.rows));}
});
test('confirmation scoring and improvement claims remain unsupported',()=>{
  const {bundle,rows}=fixture();assert.throws(()=>assess(bundle,rows,'confirmation'));
  const r=assess(bundle,rows);assert.equal(r.fresh_confirmation_verified,false);
  assert.equal(r.provider_attestation_verified,false);assert.equal(r.promotion,false);assert.equal(r.leaderboard_gain,false);
});
test('unknown failure usage preserves assigned denominator without invented MetaHarness cost',()=>{
  const {bundle,rows}=fixture([0,0,0,0]);
  Object.assign(rows[0],{category:'provider',semantic_reward:null,terminal_reward_observed:null,
    generation_tokens:null,finish_reason:null,response_id:null});
  Object.assign(rows[1],{category:'budget',semantic_reward:null,terminal_reward_observed:null,
    generation_tokens:0,finish_reason:null,call_id:null,response_id:null,reservation_label:null});
  const before=structuredClone(rows);const r=assess(bundle,rows);
  assert.equal(r.attempts,8);assert.equal(r.attempts_per_arm,4);
  assert.equal(r.groups[0].native_categories.provider,1);
  assert.equal(r.groups[0].native_categories.budget,1);
  assert.equal(r.groups[0].metaharness,null);
  assert.equal(r.groups[0].metaharness_unavailable_reason,'unknown_generation_usage');
  assert.equal(r.metaharness_groups_scored,1);assert.equal(r.metaharness_complete,false);
  assert.equal(r.unknown_generation_usage_attempts,1);assert.equal(r.full_rate_delta,0);
  assert.throws(()=>project(rows[0]));assert.deepEqual(rows,before);
});
test('unknown semantic usage remains invalid and wholly unavailable usage invokes no fitness',()=>{
  const {bundle,rows}=fixture();rows[0].generation_tokens=null;
  assert.throws(()=>assess(bundle,rows));
  for(const row of rows)Object.assign(row,{category:'provider',semantic_reward:null,
    terminal_reward_observed:null,generation_tokens:null,finish_reason:null,response_id:null});
  const r=assess(bundle,rows);assert.equal(r.actual_module,null);
  assert.equal(r.metaharness_groups_scored,0);assert.equal(r.unknown_generation_usage_attempts,8);
  assert.equal(r.full_rate_delta,0);assert.equal(r.model_improvement_claim,false);
});

test('computed-feedback first prompts cannot differ across arms',()=>{
 const x=fixture();const changed=hash('different first prompt');
 x.bundle.screen_groups[0].arms[arms[1]].prompt_sha256=changed;
 for(const row of x.rows)if(row.arm===arms[1])row.prompt_sha256=changed;
 assert.throws(()=>assess(x.bundle,x.rows),/identical first prompts/);
});
