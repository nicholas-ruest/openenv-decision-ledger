import {assess} from './assess_qualification.mjs';
export function assessArchive(a){
 if(a?.kind!=='qualification_phase_assembly'||a.scripted!==true||a.live_evidence!==false||a.assigned!==8||a.rows?.length!==8||a.all_assigned_in_denominator!==true)throw Error('eight assigned scripted archive outcomes required');
 if(a.complete===true&&a.independently_replayed===8&&a.rows.every(r=>r.replayed&&r.recorded))return assess({...a,kind:'failure_advice_qualification'});
 return {kind:'failure_advice_incomplete_qualification',assigned:8,recorded:a.recorded,unexecuted:a.unexecuted,actual_module:null,
   metaharness_suppressed_reason:'incomplete_or_unreplayed_assignments',scripted:true,live_evidence:false,selection_passed:false,promotion:false,model_improvement:false,leaderboard_gain:false};
}
