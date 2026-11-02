"""Integration with mocked Native reconstruction and synthetic leased artifacts only."""
import copy,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import parent_audit as p
import case_archive as archive
from test_archive_custody import fixture

class ParentAudit(unittest.TestCase):
    def setup_case(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);root=Path(temp.name);output=root/'archive';output.mkdir()
        f=fixture();f['archive']=str(output);f['binding']['archive']=f['launch']['archive']=str(output)
        for row,attempt in zip(f['report']['rows'],f['attempts']):
            fields=dict(failure_origin='native_semantic_outcome',terminal_reward_observed=1,generation_tokens=100,native_observation_tokens=20,completion_with_observations=120,controller_actions=[],computed_relation_exposed=False,usable_relation_counterexample_exposed=False,final_domain_reminder_presented=row['job']['arm']=='final_domain_reminder',final_domain_reminder_exposed=row['job']['arm']=='final_domain_reminder',finish_reason='stop')
            row.update(fields);attempt['record'].update(fields)
            path=output/row['job']['attempt_id'];path.mkdir();(path/'record.json').write_text(json.dumps(attempt['record']))
            for i,r in enumerate(attempt['requests']):(path/('request-'+str(i)+'.json')).write_text(json.dumps(r))
        f['report'].update(replay_only=True,provider_provenance_attested=False,execution_authorized=False,selection_passed=False,model_improvement=False,case_audit_sha256='a'*64)
        for suffix,value in [('.launch.json',f['launch']),('.worker-startup.json',f['startup'])]:output.with_suffix(suffix).write_text(json.dumps(value))
        output.with_suffix('.supervision.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in f['events']))
        (output/'worker-binding.json').write_text(json.dumps(f['binding']));(output/'complete.json').write_text(json.dumps(f['summary']))
        before=root/'before.jsonl';before.write_bytes(f['before']);after=root/'after.jsonl';after.write_bytes(f['after'])
        hashes={str(x):p.gate.sha(x) for x in list(output.rglob('*'))+[output.with_suffix(s) for s in ('.launch.json','.worker-startup.json','.supervision.jsonl')] if x.is_file()}
        bundle=root/'leases.json';value=dict(kind='final-domain-cue-parent-audit-leases',source=f['source'],method_sha256=p.gate.method_hashes(),case_audit_sha256='a'*64,archive=str(output),artifacts=hashes,ledger_before=dict(path=str(before),sha256=p.gate.sha(before)),ledger_after=dict(path=str(after),sha256=p.gate.sha(after)),prices=f['prices']);bundle.write_text(json.dumps(value))
        args=SimpleNamespace(expected_source=f['source'],audit_bundle=bundle,audit_bundle_sha256=p.gate.sha(bundle))
        case=dict(jobs=[r['job'] for r in f['report']['rows']],case_audit_sha256='a'*64)
        return output,args,case,f,value
    def test_public_seals_refuse_before_argument_or_private_reads(self):
        with patch.object(Path,'read_bytes',side_effect=AssertionError('private read')):
            with self.assertRaisesRegex(ValueError,'unsealed'):p.audit('/not-read',None,object())
    def test_complete_pipeline_uses_actual_pinned_assessment_without_authority(self):
        output,args,case,f,_=self.setup_case()
        with patch.object(p.gate,'require_case',return_value=case),patch.object(archive,'assemble',return_value=f['report']):r=p.audit(output,None,args)
        self.assertTrue(r['custody_consistent']);self.assertEqual(r['assessment']['actual_module'],'fitness.mjs:scoreCell')
        for k in ['provider_provenance_attested','actual_credit_verified','root_current_spending_attested','selection_passed','confirmation_authorized','execution_authorized','model_improvement']:self.assertIs(r[k],False)
    def test_changed_bundle_or_artifact_stops_before_reconstruction(self):
        for target in ['bundle','artifact']:
            output,args,case,f,_=self.setup_case();path=args.audit_bundle if target=='bundle' else output/'complete.json';path.write_text(path.read_text()+' ')
            with patch.object(p.gate,'require_case',return_value=case),patch.object(archive,'assemble') as replay:
                with self.assertRaisesRegex(ValueError,'lease changed'):p.audit(output,None,args)
                replay.assert_not_called()
    def test_artifact_changed_during_replay_refuses(self):
        output,args,case,f,_=self.setup_case()
        def replay(*a):output.with_suffix('.launch.json').write_text('{}');return f['report']
        with patch.object(p.gate,'require_case',return_value=case),patch.object(archive,'assemble',side_effect=replay):
            with self.assertRaisesRegex(ValueError,'changed during audit'):p.audit(output,None,args)
    def test_missing_inventory_refuses(self):
        output,args,case,f,value=self.setup_case();value['artifacts'].pop(str(output/'complete.json'));args.audit_bundle.write_text(json.dumps(value));args.audit_bundle_sha256=p.gate.sha(args.audit_bundle)
        with patch.object(p.gate,'require_case',return_value=case),patch.object(archive,'assemble') as replay:
            with self.assertRaisesRegex(ValueError,'inventory required'):p.audit(output,None,args)
            replay.assert_not_called()
    def test_incomplete_phase_retains_denominator_without_fitness_or_terminal_credit(self):
        output,args,case,f,_=self.setup_case();f['report'].update(all_terminal_attempts_reconstructed=False);f['report']['rows'][0].update(unknown_usage=True,generation_tokens=None)
        with patch.object(p.gate,'require_case',return_value=case),patch.object(archive,'assemble',return_value=f['report']),patch.object(p.subprocess,'run',side_effect=AssertionError('must not score incomplete')):
            r=p.audit(output,None,args)
        self.assertEqual(r['assigned'],8);self.assertEqual(r['unknown_usage_attempts'],1);self.assertFalse(r['fitness_computed']);self.assertFalse(r['custody_consistent'])
if __name__=='__main__':unittest.main()
