"""Guarded original constructor delegation and conservative two-phase preflight."""
import fcntl,hashlib,importlib.util,json
from pathlib import Path
import live_gate as gate
ROOT=Path(__file__).resolve().parents[2]
if Path(gate.__file__).resolve()!=Path(__file__).with_name('live_gate.py').resolve():raise ValueError('exact sibling case gate required')

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def verify_pins():
    value=json.loads(Path(__file__).with_name('financial-source-pins.json').read_text())
    if any(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h for p,h in value.items()):raise ValueError('original financial/provider protection changed')

def original_backend(args):
    case=gate.require_case(args) # Before private billing artifacts, Native/provider construction or credentials.
    gate.source_guard(args.expected_source);verify_pins();gate.operating_seconds()
    module=load('late_domain_original_financial_backend',ROOT/'research/software-public-pass-confirmation-20261031/caller.py')
    original=module.LiveBackend(args.receipt,args.reconciliation,args.tokenizer,args.amendment_sha256)
    if original.scripted is not False:raise ValueError('original real backend identity required')
    return original,case

def preflight_complete_plan(original,deadline):
    # No reservation, counter reset/refund, receipt refresh or call is performed.
    budget=original.budget
    with budget.ledger.open('rb') as f:
        fcntl.flock(f,fcntl.LOCK_SH);raw=f.read();used=budget._reserved(raw)
        if budget.receipt_sha256 is None or budget.ledger_prefix!=raw or hashlib.sha256(budget.path.read_bytes()).hexdigest()!=budget.receipt_sha256:raise ValueError('fresh exact existing accounting leases required')
        remaining=budget.cap-used
        quote=load('late_domain_original_phase_quote',ROOT/'scripts/stage-phase-admission.py')
        pair=quote.admit(32,[28672]*32,8096,original.frozen['provider']['pricing'],min(remaining,original.credit))
        if not pair['admitted']:raise ValueError('screen and conditional confirmation exceed existing allocation or actual credit')
    original.admit([28672]*16,8096,deadline) # Original per-phase cumulative and deadline protections remain.
    return dict(pair,reservation_performed=False,execution_authorized=False,scope='screen plus conditional confirmation only; no case or model calls')
