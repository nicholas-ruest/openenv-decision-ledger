"""Pure whole-phase budget admission. Does not reserve funds or launch calls."""
from decimal import Decimal, InvalidOperation


def amount(value):
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("valid decimal required") from exc
    if not result.is_finite() or result < 0:
        raise ValueError("finite nonnegative amount required")
    return result


def admit(calls, prompt_bounds, generated_bound, prices, remaining):
    if (type(calls) is not int or calls < 1 or len(prompt_bounds) != calls or
            any(type(v) is not int or v <= 0 for v in prompt_bounds) or
            type(generated_bound) is not int or generated_bound <= 0):
        raise ValueError("complete bounded phase required")
    input_price, output_price = amount(prices["input"]), amount(prices["output"])
    # Match DollarReservations' per-call 10% margin, without resetting/refunding it.
    costs = [(Decimal(v) * input_price + Decimal(generated_bound) * output_price)
             * Decimal("1.10") / Decimal(1_000_000) for v in prompt_bounds]
    total = sum(costs, Decimal(0))
    return {"admitted": total <= amount(remaining), "quoted_usd": str(total),
            "call_quotes_usd": list(map(str, costs)), "calls": calls,
            "reservation_performed": False,
            "requirements": "Caller must reconcile billing, lock/check remaining ledger, and reserve before each call."}
