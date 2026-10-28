import test from 'node:test';
import assert from 'node:assert/strict';
import {analysePhase,compatibleRow,illustrativePowerOnly,classifyEpisode,scoreCell} from './adapter.mjs';

const hash=x=>x.toString(16).padStart(64,'0');
function fixture(){return Array.from({length:16},(_,i)=>{
  const group=Math.floor(i/4),sample=i%4;
  return {phase:'screen',task_id:'qe_skill-media-d'+(group<2?1:2),family:group%2?'timecode':'catalogue',
    seed:100+group,sample,case_sha256:hash(group),workspace_sha256:hash(10+group),category:sample===0?'wrong':'full',
    semantic_reward:sample===0?0:1,terminal_reward_observed:sample===0?0:1,generation_tokens:20,
    call_ids:[hash(100+i)],response_ids:[hash(200+i)],reservation_labels:['fiction-'+i]};
});}

test('actual pinned MetaHarness scores four same-case mixed groups',()=>{
  const r=analysePhase(fixture());assert.equal(r.productive_same_case_groups,4);assert.equal(r.groups[0].eligible,4);
  assert.equal(r.is_training,false);assert.equal(r.promotion,false);
});
test('upstream reward1 failure precedence is guarded without altering raw evidence',()=>{
  assert.equal(classifyEpisode({type:'episode',reward:1,failure:'step_budget_exhausted'}),'solved');
  const row=fixture()[1];row.category='budget';row.semantic_reward=null;const before=JSON.stringify(row);
  assert.equal(classifyEpisode(compatibleRow(row)),'infra');assert.equal(compatibleRow(row).compatibility.observed_native_reward,1);
  assert.equal(JSON.stringify(row),before);
});
test('between-case variance cannot manufacture within-case signal',()=>{
  const rows=fixture();rows.forEach((r,i)=>{r.category=i<8?'full':'wrong';r.semantic_reward=i<8?1:0;r.terminal_reward_observed=r.semantic_reward;});
  assert.ok(scoreCell(rows.map(compatibleRow)).signal>0);
  assert.equal(analysePhase(rows).productive_same_case_groups,0);
});
test('every native failure remains ineligible and separately counted',()=>{
  for(const category of ['format','provider','truncation','execution','budget']){
    const rows=fixture();rows[0].category=category;rows[0].semantic_reward=null;
    const r=analysePhase(rows);assert.equal(r.groups[0].signal,0);assert.equal(r.groups[0].eligible,3);
    assert.equal(r.groups[0].native_failure_breakdown[category],1);
  }
});
test('format stop fact is mapped without fabricated token metrics',()=>{
  const r=fixture()[0];r.category='format';r.semantic_reward=null;const p=compatibleRow(r);
  assert.equal(classifyEpisode(p),'format');assert.deepEqual(p.trajectory.provider_metrics,[{finish_reason:'stop'}]);
  assert.equal(p.trajectory.accounting.generation_tokens,20);
});
test('incomplete groups, phase mixing and duplicate samples reject',()=>{
  assert.throws(()=>analysePhase(fixture().slice(1)));
  const rows=fixture();rows[1].phase='confirmation';assert.throws(()=>analysePhase(rows));
  rows[1].phase='screen';rows[1].sample=0;assert.throws(()=>analysePhase(rows));
});
test('reused call, response and reservation identities reject',()=>{
  for(const key of ['call_ids','response_ids','reservation_labels']){const rows=fixture();rows[1][key]=rows[0][key];assert.throws(()=>analysePhase(rows));}
});
test('case mixing, fractional reward and missing accounting reject',()=>{
  const rows=fixture();rows[0].case_sha256=hash(1000);assert.throws(()=>analysePhase(rows));
  const row=fixture()[0];row.semantic_reward=.5;assert.throws(()=>compatibleRow(row));
  row.semantic_reward=0;row.generation_tokens=undefined;assert.throws(()=>compatibleRow(row));
});
test('upstream confirmation is explicitly not claimed for this terminal protocol',()=>{
  assert.equal(analysePhase(fixture()).direct_confirmation_supported,false);
  const p=illustrativePowerOnly();assert.equal(p.applied_to_actual_protocol,false);assert.equal(p.reachable,false);assert.equal(p.blocksNeeded,8);
});
