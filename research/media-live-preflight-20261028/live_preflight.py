"""Read-only live-evidence/budget preview. NEVER grants execution authority.

Inputs must come from private reconciliation. Hashes/flags bind a supplied
snapshot; they do not establish account truth or authenticate a provider.
No file writes, reservations, credential access or network operations occur.
"""
from datetime import datetime, timezone
from decimal import Decimal

from media_protocol import digest
from trajectory_audit import PLAN_BODY_SHA256, require, sha


def amount(x):
    require(type(x) in (str,int,float,Decimal),'explicit finite decimal required')
    value=Decimal(str(x));require(value.is_finite() and value>=0,'finite nonnegative amount required')
    return value


def age(stamp, now):
    value=datetime.fromisoformat(stamp)
    require(value.tzinfo is not None,'timezone-aware observation required')
    seconds=(now-value.astimezone(timezone.utc)).total_seconds()
    require(0<=seconds<=7200,'fresh actual observation required')


def no_synthetic(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if key in ('callbacks_synthetic','provider_fields_synthetic','scripted_oracle_controls','outcomes_are_scripted_not_model_measured'):
                require(item is False,'synthetic fixture cannot be live evidence')
            if key in ('synthetic_calls','scripted_provider_records'):
                require(type(item) is int and item==0,'scripted call records cannot be live evidence')
            no_synthetic(item)
    elif isinstance(value,list):
        for item in value:no_synthetic(item)


def preview(plan, phase, receipt, ledger, inventory, observation, provider, expected_provider_sha256,
            *, now, admission_module):
    """One existing allocation, complete media phase, immutable snapshot binding.

    inventory supplies the externally pinned original allocation identity/cap,
    carry-forward prior-spend floor and all parent-receipt/ledger hashes. It is
    not created or updated here. Pure quote helper is the existing
    scripts/stage-phase-admission.py, preserving its10% reservation margin.
    """
    require(digest(plan)==PLAN_BODY_SHA256 and phase in plan['phases'],'frozen complete media phase required')
    require(now.tzinfo is not None,'explicit aware current time required')
    for obj in (receipt,ledger,inventory,observation,provider):no_synthetic(obj)
    require(observation.get('evidence_kind')=='live_reconciled_snapshot','live private observation required')
    require(observation.get('actual_credit_usage_verified') is True and observation.get('all_existing_receipts_reconciled') is True,'external actual reconciliation required')
    require(receipt.get('closed_for_new_calls') is not True,'existing allocation closed')
    require(receipt['allocation_id']==inventory['allocation_id'],'original allocation identity required')
    cap=amount(receipt['screen_cap_usd']);prior=amount(receipt['prior_spend_usd'])
    require(0<cap<=2 and cap==amount(inventory['screen_cap_usd']),'existing allocation cap cannot change')
    require(prior>=amount(inventory['prior_spend_usd']),'carry-forward spend cannot reset')
    require(prior+cap<=amount(receipt['total_authorized_usd']),'allocation exceeds cumulative authorization')
    age(receipt['checked_at'],now);age(observation['observed_at'],now)
    require(observation['observed_at']==receipt['checked_at'],'receipt timestamp must bind actual observation')
    parents=inventory['parent_file_hashes']
    require(isinstance(parents,dict) and bool(parents) and all(sha(h) for h in parents.values()),'complete pinned parent hashes required')
    require(observation['parent_file_hashes']==parents,'parent reconciliation inventory mismatch')
    require(observation['receipt_sha256']==digest(receipt) and observation['ledger_sha256']==digest(ledger),'actual receipt/ledger snapshot mismatch')
    require(amount(observation['prior_spend_usd'])==prior,'observed carry-forward spend mismatch')
    labels=set();used=Decimal(0)
    for row in ledger:
        require(isinstance(row['label'],str) and row['label'] and row['label'] not in labels,'unique existing reservation labels required')
        labels.add(row['label']);used+=amount(row['usd'])
        require(type(row['prompt_bound']) is int and row['prompt_bound']>0 and type(row['generation_bound']) is int and row['generation_bound']>0,'valid existing reservation bounds required')
    require(used<=cap,'existing reservation cap exhausted/overdrawn')
    remaining=cap-used
    require(used==amount(observation['reserved_usd']),'actual observed reservation total mismatch')
    balance=amount(receipt['prepaid_balance_usd'])
    require(balance==amount(observation['prepaid_balance_usd']) and cap<=balance,'actual prepaid balance insufficient for existing allocation')
    age(provider['observed_at'],now)
    require(sha(expected_provider_sha256) and digest(provider['catalog_row'])==expected_provider_sha256,'frozen actual provider fingerprint mismatch')
    row=provider['catalog_row'];route=row['provider']
    require(row['id']==plan['sampling']['model'] and route['provider']==plan['sampling']['route'] and route['status']=='live','selected live provider/model required')
    prices=route['pricing'];inp,out=amount(prices['input']),amount(prices['output'])
    require(inp<=1 and 0<out<=3,'existing frozen price bounds required')
    phase_data=plan['phases'][phase];episodes=phase_data['future_rollouts'];calls=plan['maximum_provider_calls_per_phase']
    require(episodes==16 and calls==512,'whole phase bounds cannot shrink')
    # Prompt cost pessimistically uses the full context for all512 calls. Output
    # is bounded by16 episode-level generation budgets, NOT512 full generations.
    # Reuse existing per-call quote margin, then add the remaining shared output.
    base=admission_module.admit(calls,[plan['sampling']['context_units']]*calls,1,prices,remaining)
    shared_output=episodes*plan['sampling']['episode_generation_units']
    total=amount(base['quoted_usd'])+Decimal(shared_output-calls)*out*Decimal('1.10')/Decimal(1_000_000)
    return {'budget_feasible':total<=remaining,'complete_phase_quoted_usd':str(total),
            'remaining_existing_allocation_usd':str(remaining),'calls_bound':calls,'episode_generation_bound':shared_output,
            'snapshot_sha256':digest({'receipt':receipt,'ledger':ledger,'inventory':inventory,'observation':observation,'provider':provider}),
            'execution_authorized':False,'reservation_performed':False,'account_truth_authenticated':False,
            'requirements':'External private reconciliation, ledger lock/recheck, provider/source attestation and append-before-call reservation remain mandatory.'}
