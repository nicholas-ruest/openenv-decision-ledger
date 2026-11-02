"""Leased read-only parent audit. No provider, account attestation or execution authority."""
import hashlib,json,subprocess
from pathlib import Path
import live_gate as gate
HERE=Path(__file__).resolve().parent

def need(value,message):
    if not value:raise ValueError(message)

def read_leased(item):
    need(set(item)=={'path','sha256'} and gate.sealed(item['sha256']),'exact file/hash lease required')
    path=Path(item['path']);need(path.is_absolute() and not path.is_symlink(),'absolute original artifact required')
    raw=path.read_bytes();need(hashlib.sha256(raw).hexdigest()==item['sha256'],'artifact lease changed')
    return raw

def modules():
    import case_archive,archive_custody
    need(all(Path(m.__file__).resolve()==HERE/(m.__name__+'.py') for m in (case_archive,archive_custody)),'exact original audit modules required')
    return case_archive,archive_custody

def audit(output,counter,args):
    case=gate.require_case(args) # All existing immutable case/source/inventory checks precede reads or Native.
    output=Path(output).resolve()
    need(gate.sealed(args.audit_bundle_sha256),'immutable audit bundle lease required')
    bundle=json.loads(read_leased(dict(path=str(Path(args.audit_bundle).absolute()),sha256=args.audit_bundle_sha256)))
    need(bundle.get('kind')=='final-domain-cue-parent-audit-leases' and bundle.get('source')==args.expected_source and bundle.get('method_sha256')==gate.method_hashes() and bundle.get('case_audit_sha256')==case['case_audit_sha256'] and bundle.get('archive')==str(output),'exact original audit methods, case and archive required')
    siblings=[output.with_suffix(s) for s in ('.supervision.jsonl','.launch.json','.worker-startup.json')]
    files=sorted([p for p in output.rglob('*') if p.is_file()]+siblings)
    need(not any(p.is_symlink() for p in files) and set(bundle['artifacts'])=={str(p) for p in files},'complete original artifact inventory required')
    snapshots={str(p):read_leased(dict(path=str(p),sha256=bundle['artifacts'][str(p)])) for p in files}
    before=read_leased(bundle['ledger_before']);after=read_leased(bundle['ledger_after'])
    original,custody=modules();need(after.startswith(before),'all retained ledger bytes required');custody.ledger(before);custody.ledger(after)
    report=original.assemble(output,counter,args)
    base=dict(kind='final_domain_cue_parent_audit',assigned=8,all_assigned_in_denominator=True,provider_provenance_attested=False,actual_credit_verified=False,root_current_spending_attested=False,execution_authorized=False,selection_passed=False,confirmation_authorized=False,model_improvement=False,is_training=False)
    if not report['all_terminal_attempts_reconstructed']:
        result=dict(base,complete=False,custody_consistent=False,fitness_computed=False,unknown_usage_attempts=sum(r.get('unknown_usage') is True for r in report['rows']))
    else:
        def saved(path):return json.loads(snapshots[str(path)])
        attempts=[]
        for job in case['jobs']:
            path=output/job['attempt_id'];record=saved(path/'record.json')
            attempts.append(dict(record=record,requests=[saved(path/('request-'+str(i)+'.json')) for i in range(len(record['calls']))],response_ids=record['response_ids']))
        checked=custody.check(events=[json.loads(x) for x in snapshots[str(siblings[0])].splitlines() if x],binding=saved(output/'worker-binding.json'),startup=saved(siblings[2]),launch=saved(siblings[1]),summary=saved(output/'complete.json'),report=report,attempts=attempts,before=before,after=after,prices=bundle['prices'],source=args.expected_source,archive=str(output))
        module=(HERE/'assess_reconstruction.mjs').as_uri()
        script="import {readFileSync} from 'node:fs';import {assessReconstruction} from "+json.dumps(module)+";console.log(JSON.stringify(assessReconstruction(JSON.parse(readFileSync(0,'utf8')))));"
        value=subprocess.run(['node','--input-type=module','-e',script],input=json.dumps(report,allow_nan=False),text=True,capture_output=True,check=True)
        assessment=json.loads(value.stdout)
        need(assessment['selection_passed'] is False and assessment['confirmation_authorized'] is False,'read-only assessment cannot promote authority')
        result=dict(base,complete=True,custody_consistent=checked['consistent'],fitness_computed=assessment['fitness_computed'],custody=checked,assessment=assessment)
    # Refuse files changed while replay/assessment ran, including added/missing files.
    need({str(p) for p in output.rglob('*') if p.is_file()}|{str(p) for p in siblings}==set(snapshots),'artifact inventory changed during audit')
    for path,raw in snapshots.items():need(Path(path).read_bytes()==raw,'artifact changed during audit')
    need(read_leased(bundle['ledger_before'])==before and read_leased(bundle['ledger_after'])==after,'ledger snapshots changed during audit')
    read_leased(dict(path=str(Path(args.audit_bundle).absolute()),sha256=args.audit_bundle_sha256))
    return result
