// Software-specific projection over pinned, unmodified MIT MetaHarness fitness.
// Offline analysis only. No provider, training, admission or promotion authority.
import {PIN,scoreCell} from '../metaharness-compatibility-20261028/adapter.mjs';
const need=(x,m)=>{if(!x)throw Error(m);};
const sha=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
const count=x=>Number.isSafeInteger(x)&&x>=0;
const arms=['review_control','public_check'];
const semantic=['full','partial','wrong'];
const failure={format:'invalid_json_action',edit_rejection:'invalid_json_action',
  execution:'environment_step_failed',provider:'provider_request_failed',
  budget:'global_token_budget_exhausted',truncation:'completion_truncated'};

function validate(row){
  need(row&&[...semantic,...Object.keys(failure)].includes(row.category),'audited category required');
  need(count(row.generation_tokens)||(row.generation_tokens===null&&!semantic.includes(row.category)),
    'observed generation count required for semantic results; failures may explicitly retain unknown usage');
  const r=row.semantic_reward;
  if(row.category==='full')need(r===1,'full reward mismatch');
  else if(row.category==='wrong')need(r===0,'wrong reward mismatch');
  else if(row.category==='partial')need(Number.isFinite(r)&&r>0&&r<1,'partial reward mismatch');
  else need(r===null,'failures have no semantic reward');
  need(row.terminal_reward_observed===null||(Number.isFinite(row.terminal_reward_observed)&&row.terminal_reward_observed>=0&&row.terminal_reward_observed<=1),'observed native reward required or explicit null');
  if(semantic.includes(row.category))need(row.terminal_reward_observed===r,'semantic/native mismatch');
  need(row.finish_reason===null||typeof row.finish_reason==='string','observed finish reason or explicit null required');
}

export function project(row){
  validate(row);
  need(count(row.generation_tokens),'unknown usage cannot be projected into MetaHarness token accounting');
  const r=row.semantic_reward;
  // Failure precedence is explicit: a budget auto-grade of 1 is never solved.
  // Unknown finish reason is kept unknown; no manufactured stop metric.
  return {type:'episode',seed:row.seed,attempt:row.sample,reward:r??0,
    failure:failure[row.category]??null,
    trajectory:{accounting:{generation_tokens:row.generation_tokens},
      provider_metrics:[{finish_reason:row.finish_reason}]}};
}

export function assess(bundle,rows,phase='screen'){
  need(phase==='screen','only frozen screen inputs supported; confirmation requires separate attested input binding');
  need(bundle?.confirmation_observations_materialized===false,'frozen protocol bundle required');
  const jobs=bundle[phase+'_jobs'];
  need(Array.isArray(jobs)&&jobs.length===8&&Array.isArray(rows)&&rows.length===8,'complete 8-assignment phase required');
  const assigned=new Map(),groups=new Map();
  for(const job of jobs){
    need(job.phase===phase&&arms.includes(job.arm)&&count(job.seed)&&count(job.sample)&&job.sample<4&&sha(job.attempt_id),'invalid assignment');
    need(['software_repair-ignore-d3'].includes(job.task_id)&&[2660000].includes(job.seed),'frozen screen task/seed scope required');
    need(typeof bundle.namespace==='string'&&bundle.namespace&&job.namespace===bundle.namespace,'single frozen namespace required');
    need(!assigned.has(job.attempt_id),'duplicate assigned identity');assigned.set(job.attempt_id,job);
    const key=JSON.stringify([job.task_id,job.seed,job.arm]);
    const g=groups.get(key)??[];
    need(!g.some(x=>x.sample===job.sample),'duplicate assigned sample');g.push(job);groups.set(key,g);
  }
  need(groups.size===2&&[...groups.values()].every(g=>g.length===4),'one paired case with four samples per arm required');
  const seen=new Set(),callIDs=new Set(),responseIDs=new Set(),reservations=new Set();
  const observed=new Map();
  for(const row of rows){
    const job=assigned.get(row.attempt_id);
    need(job&&!seen.has(row.attempt_id),'unassigned or duplicate result');seen.add(row.attempt_id);
    for(const k of ['namespace','phase','task_id','seed','sample','arm'])need(row[k]===job[k],'assignment identity mismatch');
    need(sha(row.prompt_sha256)&&sha(row.problem_sha256),'audited prompt/problem hashes required');
    if(phase==='screen'){
      const g=bundle.screen_groups.find(g=>g.task_id===job.task_id&&g.seed===job.seed);
      need(g&&row.problem_sha256===g.problem_sha256&&row.prompt_sha256===g.arms[job.arm].prompt_sha256,'frozen input mismatch');
    }
    // IDs are supplied evidence, not independently verified provider attestations.
    // Provider failures may have no response ID; budget failures may have no call.
    for(const [field,ids,emptyAllowed] of [['call_id',callIDs,row.category==='budget'],['response_id',responseIDs,['provider','budget'].includes(row.category)],['reservation_label',reservations,row.category==='budget'&&row.call_id===null]]){
      if(row[field]===null&&emptyAllowed)continue;
      need(typeof row[field]==='string'&&row[field]&&!ids.has(row[field]),'missing or reused '+field);ids.add(row[field]);
    }
    validate(row);observed.set(row.attempt_id,row);
  }
  const scored=[...groups.values()].map(jobs=>{
    const rs=jobs.map(j=>observed.get(j.attempt_id));
    need(new Set(rs.map(r=>r.prompt_sha256)).size===1&&new Set(rs.map(r=>r.problem_sha256)).size===1,'not a same-prompt sample group');
    const unknownUsage=rs.filter(r=>r.generation_tokens===null).length;
    // Descriptive outcomes survive missing usage. Never invent a cost just to
    // obtain an upstream fitness score or silently drop the failed attempt.
    const score=unknownUsage===0?scoreCell(rs.map(project)):null;
    return {task_id:rs[0].task_id,seed:rs[0].seed,arm:rs[0].arm,
      problem_sha256:rs[0].problem_sha256,attempts:4,full:rs.filter(r=>r.category==='full').length,
      semantic_sum:rs.reduce((a,r)=>a+(r.semantic_reward??0),0),
      native_categories:Object.fromEntries([...semantic,...Object.keys(failure)].map(c=>[c,rs.filter(r=>r.category===c).length])),
      unknown_generation_usage_attempts:unknownUsage,
      metaharness_unavailable_reason:unknownUsage?'unknown_generation_usage':null,
      metaharness:score?{signal:score.signal,eligible:score.eligible,solved:score.solved,partial:score.partial,
        reasoning:score.reasoning,format:score.format,truncation:score.truncation,infra:score.infra}:null};
  });
  const pairs=scored.filter(g=>g.arm===arms[0]).map(a=>{
    const b=scored.find(g=>g.task_id===a.task_id&&g.seed===a.seed&&g.arm===arms[1]);
    need(b&&b.problem_sha256===a.problem_sha256,'paired problem mismatch');
    return {task_id:a.task_id,seed:a.seed,full_rate_delta:(b.full-a.full)/4,
      semantic_mean_delta:(b.semantic_sum-a.semantic_sum)/4};
  });
  return {screen_selection_passed:rows.every(r=>r.generation_tokens!==null&&!['provider','budget'].includes(r.category))&&pairs.some(p=>p.full_rate_delta>0)&&pairs.every(p=>p.full_rate_delta>=0)&&pairs.reduce((a,p)=>a+p.semantic_mean_delta,0)>=0,phase,attempts:8,attempts_per_arm:4,paired_groups:1,
    procedural_seeds:new Set(jobs.map(j=>j.seed)).size,groups:scored,pairs,
    full_rate_delta:pairs.reduce((a,p)=>a+p.full_rate_delta,0),
    semantic_mean_delta:pairs.reduce((a,p)=>a+p.semantic_mean_delta,0),
    metaharness_source:PIN,actual_module:scored.some(g=>g.metaharness)?'fitness.mjs:scoreCell':null,
    metaharness_groups_scored:scored.filter(g=>g.metaharness).length,
    metaharness_complete:scored.every(g=>g.metaharness!==null),
    unknown_generation_usage_attempts:rows.filter(r=>r.generation_tokens===null).length,
    all_assigned_attempts_in_denominator:true,provider_attestation_verified:false,
    fresh_confirmation_verified:false,model_improvement_claim:false,leaderboard_gain:false,
    promotion:false,is_training:false};
}
