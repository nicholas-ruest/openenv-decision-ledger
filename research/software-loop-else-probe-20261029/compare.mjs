// Paired runtimes deliberately share replies; they are not independent calls.
import {readFileSync,writeFileSync} from 'node:fs';
import {PIN,scoreCell} from '../metaharness-compatibility-20261028/adapter.mjs';
import {project} from '../software-function-assessment-20261028/assess.mjs';
const [oldPath,newPath,output]=process.argv.slice(2);
const old=JSON.parse(readFileSync(oldPath)),candidate=JSON.parse(readFileSync(newPath));
const need=(x,m)=>{if(!x)throw Error(m);};
need(old.live_archive_verified===true&&candidate.live_archive_verified===true&&old.scripted===false&&candidate.scripted===false,'scripted controls cannot confirm');
need(old.assigned===8&&candidate.assigned===8&&old.rows.length===8&&candidate.rows.length===8,'complete eight-assignment grades required');
need(old.inputs_sha256===candidate.inputs_sha256&&old.runtime==='9d1a28a3357f87349bcbc81166a2c1191c2d03c6'&&candidate.runtime==='b3a8873a4629a1cb34d2dfd7b297895783d9af9e','exact paired runtime/input pins required');
const ids=new Set(),pairs=[];
for(let i=0;i<8;i++){
 const a=old.rows[i],b=candidate.rows[i];
 for(const k of ['attempt_id','task_id','seed','sample','response_id','call_id','raw_response_sha256','generation_tokens','finish_reason','prompt_sha256','problem_sha256'])need(a[k]===b[k],'paired reply/input differs: '+k);
 need(!ids.has(a.attempt_id),'duplicate assignment');ids.add(a.attempt_id);
 need([2540000,2540100].includes(a.seed)&&a.sample>=0&&a.sample<4,'disjoint confirmation scope required');
 pairs.push({task_id:a.task_id,seed:a.seed,sample:a.sample,old_category:a.category,new_category:b.category,old_semantic:a.semantic_reward,new_semantic:b.semantic_reward});
}
const groups=[];
for(const [runtime,data] of [['baseline',old],['candidate',candidate]]){
 for(const task of ['software_repair-ignore-d3','software_repair-ignore-d4']){
  const rs=data.rows.filter(r=>r.task_id===task);
  need(rs.length===4&&new Set(rs.map(r=>r.sample)).size===4&&new Set(rs.map(r=>r.prompt_sha256)).size===1,'four same-prompt samples required');
  const known=rs.every(r=>Number.isSafeInteger(r.generation_tokens));
  const s=known?scoreCell(rs.map(project)):null;
  groups.push({runtime,task_id:task,attempts:4,full:rs.filter(r=>r.category==='full').length,semantic_sum:rs.reduce((s,r)=>s+(r.semantic_reward??0),0),categories:Object.fromEntries([...new Set(rs.map(r=>r.category))].map(c=>[c,rs.filter(r=>r.category===c).length])),metaharness:s?{signal:s.signal,eligible:s.eligible,solved:s.solved,partial:s.partial,reasoning:s.reasoning,format:s.format,truncation:s.truncation,infra:s.infra}:null});
 }
}
const delta=pairs.reduce((s,p)=>s+(p.new_category==='full')-(p.old_category==='full'),0);
const semantic=pairs.reduce((s,p)=>s+(p.new_semantic??0)-(p.old_semantic??0),0);
const complete=old.rows.every(r=>r.response_id&&r.raw_response_sha256&&Number.isSafeInteger(r.generation_tokens));
const result={assigned_model_calls:8,paired_runtime_grades:16,shared_responses_are_not_independent_calls:true,full_solve_count_delta:delta,semantic_mean_delta:semantic/8,pairs,groups,metaharness_source:PIN,actual_module:'fitness.mjs:scoreCell',fresh_runtime_compatibility_confirmation:complete&&delta>0&&semantic>=0&&pairs.every(p=>(p.new_semantic??0)>=(p.old_semantic??0)),model_training:false,model_weight_improvement_claim:false,leaderboard_gain:false,promotion:false};
writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({full_solve_count_delta:delta,semantic_mean_delta:semantic/8,confirmed:result.fresh_runtime_compatibility_confirmation}));
