"""Pure complete-phase upper-bound quote; no credentials, reservations or inference."""
from decimal import Decimal

def quote(plan,prices,remaining):
    if (plan['attempts_per_phase']!=32 or plan['max_model_calls_per_attempt']!=2 or
        plan['max_model_calls_per_phase']!=64 or plan['max_retries']!=0 or
        plan['first_call_generation_max']!=2048 or
        plan['completion_budget_including_postreset_observations']!=4096 or plan['context_budget']!=8192):
        raise ValueError('frozen complete software revision protocol required')
    amounts=[Decimal(str(x)) for x in [prices['input'],prices['output'],remaining]]
    if any(not x.is_finite() or x<0 for x in amounts) or amounts[1]==0:
        raise ValueError('finite priced inference and nonnegative remaining amount required')
    inp,out,remaining=amounts
    # All 64 calls reserve the context cap; each of 32 attempts can generate
    # at most 2x2048 tokens. Observations consume part of that 4096 budget,
    # but are conservatively NOT deducted here. No cross-arm response reuse.
    inputs=64*8192;outputs=32*4096
    upper=(Decimal(inputs)*inp+Decimal(outputs)*out)*Decimal('1.10')/Decimal(1000000)
    return dict(calls_bound=64,prompt_token_bound=inputs,generation_token_bound=outputs,
                complete_phase_quote_usd=str(upper),remaining_existing_allocation_usd=str(remaining),
                budget_feasible=upper<=remaining,execution_authorized=False,reservation_performed=False,
                quote_kind='conservative full-context/full-generation upper bound, not expected spend',
                caveat='Requires externally attested production input/output accounting; no financial admission, identity or billing authority.')
