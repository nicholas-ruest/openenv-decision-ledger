// Adapter around unmodified MIT MetaHarness fitness code. No runner/provider.
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';

export const PIN='b8c3d38de41203faf633ef6dceb8452a4727b0ea';
const pins={
  'fitness.mjs':'852da62a33b833bc0a8cbc015891e3030d769b40fa41bf9793da84bdadfff130',
  'confirm.mjs':'fd765ce849bbf5c75925da7427464a96f8d70f43b24308d9802f287a861dd81d',
};
for(const [file,hash] of Object.entries(pins)){
  if(createHash('sha256').update(readFileSync(new URL('./upstream/'+file,import.meta.url))).digest('hex')!==hash)throw Error('upstream source pin mismatch');
}
const {classifyEpisode,scoreCell}=await import('./upstream/fitness.mjs');
const {confirmationPower}=await import('./upstream/confirm.mjs');
const require=(x,m)=>{if(!x)throw Error(m);};
const sha=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
const count=x=>Number.isSafeInteger(x)&&x>=0;
const failure={format:'invalid_json_action',provider:'provider_request_failed',truncation:'completion_truncated',execution:'environment_step_failed',budget:'global_token_budget_exhausted'};

export function compatibleRow(row){
  require(row&&['full','wrong',...Object.keys(failure)].includes(row.category),'audited classification required');
  require(count(row.generation_tokens),'recorded generation accounting required');
  const semantic=row.category==='full'?1:row.category==='wrong'?0:null;
  require(row.semantic_reward===semantic,'classification/semantic mismatch');
  if(row.terminal_reward_observed!==null&&row.terminal_reward_observed!==undefined)require([0,1].includes(row.terminal_reward_observed),'binary observed native reward required');
  // MetaHarness checks reward1 BEFORE failures. Do not feed a budget auto-grade1
  // as solved. This projection changes only an analysis copy, never raw grading.
  const projected={type:'episode',seed:row.seed,attempt:row.sample,reward:semantic??0,
    failure:failure[row.category]??null,
    trajectory:{accounting:{generation_tokens:row.generation_tokens}},
    compatibility:{original_category:row.category,semantic_reward:semantic,
      observed_native_reward:row.terminal_reward_observed??null,analysis_projection_only:true}};
  // The native auditor's format class is emitted only for a stop-terminated
  // invalid action. Preserve that fact without inventing token metrics or IDs.
  if(row.category==='format')projected.trajectory.provider_metrics=[{finish_reason:'stop'}];
  return projected;
}

export function analysePhase(rows){
  require(Array.isArray(rows)&&rows.length===16,'complete16attempt phase required');
  const groups=new Map(),calls=new Set(),responses=new Set(),labels=new Set();let phase;
  for(const row of rows){
    require(['screen','confirmation'].includes(row.phase),'known phase required');
    phase??=row.phase;require(row.phase===phase,'no phase pooling');
    require(typeof row.task_id==='string'&&typeof row.family==='string'&&count(row.seed)&&count(row.sample)&&row.sample<4,'explicit case/sample labels required');
    require(sha(row.case_sha256)&&sha(row.workspace_sha256),'audited visible case identity required');
    for(const [field,seen] of [['call_ids',calls],['response_ids',responses],['reservation_labels',labels]]){
      require(Array.isArray(row[field]),'complete observed identity arrays required');
      for(const id of row[field]){require(typeof id==='string'&&id&&!seen.has(id),'duplicate observed identity');seen.add(id);}
    }
    const key=JSON.stringify([row.task_id,row.family,row.seed,row.case_sha256,row.workspace_sha256]);
    const group=groups.get(key)??[];
    require(!group.some(r=>r.sample===row.sample),'duplicate sample');group.push(row);groups.set(key,group);
  }
  require(groups.size===4&&[...groups.values()].every(g=>g.length===4),'four complete same-case groups required');
  const scores=[...groups.values()].map(group=>{
    const projected=group.map(compatibleRow);const score=scoreCell(projected);
    return {task_id:group[0].task_id,family:group[0].family,seed:group[0].seed,
      same_case_verified:true,signal:score.signal,eligible:score.eligible,
      class_counts:{solved:score.solved,reasoning:score.reasoning,format:score.format,truncation:score.truncation,infra:score.infra},
      native_failure_breakdown:Object.fromEntries(Object.keys(failure).map(k=>[k,group.filter(r=>r.category===k).length])),
      generation_tokens:score.genTokens};
  });
  return {phase,attempts:16,groups:scores,productive_same_case_groups:scores.filter(g=>g.signal===1).length,
    metaharness_source:PIN,actual_modules_executed:['fitness.mjs:scoreCell','fitness.mjs:classifyEpisodeDetailed'],
    direct_confirmation_supported:false,
    confirmation_limitation:'Upstream pairedOutcomes uses changed genome cells and4consecutive-seed blocks; this terminal plan uses same-case repeated samples and nonconsecutive family-matched cases. No direct confirmation/promotion mapping is claimed.',
    model_improvement_claim:false,promotion:false,is_training:false};
}

export function illustrativePowerOnly(){
  return {...confirmationPower({changedCells:4,attempts:4}),
    applied_to_actual_protocol:false,reason:'No measured baseline/treatment pair or equivalent upstream seed-block plan exists.'};
}

export {classifyEpisode,scoreCell};
