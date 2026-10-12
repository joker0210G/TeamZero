"""[REFERENCE EXAMPLE / TEMPLATE FIXTURE]
Sample domain service demonstrating TeamZero invariants (SPEC-REFUND-001).
This file serves as a reference implementation for integration testing, demonstrations,
and educational walkthroughs. Real projects should define their own services.
"""

from typing import Dict, Any


def calculate_refund(
    amount_paid: float,
    days_since_purchase: int,
    item_condition: str
) -> Dict[str, Any]:
    """Calculates refund based on purchase elapsed days and item state.

    Args:
        amount_paid: Original dollar amount charged.
        days_since_purchase: Integer count of days since transaction.
        item_condition: 'unopened' or 'opened'.

    Returns:
        Dict containing refund amount, currency, and applied rule ID.

    Raises:
        ValueError: If amount_paid is negative or days_since_purchase is negative.
        TypeError: If parameter types do not conform to signature.
    """
    # Guard parameter types and reject bool subclass smuggling (EF-03)
    if isinstance(amount_paid, bool) or not isinstance(amount_paid, (int, float)):
        raise TypeError(f"amount_paid must be numeric and not bool, got {type(amount_paid).__name__}")
    if isinstance(days_since_purchase, bool) or not isinstance(days_since_purchase, int):
        raise TypeError(f"days_since_purchase must be int and not bool, got {type(days_since_purchase).__name__}")
    if not isinstance(item_condition, str):
        raise TypeError(f"item_condition must be string, got {type(item_condition).__name__}")

    # Guard non-finite numbers (NaN / inf / -inf) (EF-01, EF-02)
    import math
    if not math.isfinite(amount_paid):
        raise ValueError(f"amount_paid must be a finite number: {amount_paid}")

    # Guard negative inputs (Prevents Traps 2)
    if amount_paid < 0.0:
        raise ValueError(f"amount_paid cannot be negative: {amount_paid}")
    if days_since_purchase < 0:
        raise ValueError(f"days_since_purchase cannot be negative: {days_since_purchase}")

    clean_condition = item_condition.strip().lower()

    # Rule R1: Unopened item returned within 30 calendar days (full refund)
    if days_since_purchase <= 30 and clean_condition == "unopened":
        # EF-04: Rounding must never refund more than original amount paid
        refund_val = min(round(float(amount_paid), 2), float(amount_paid))
        return {
            "refund": refund_val,
            "currency": "USD",
            "rule_id": "R1",
            "status": "approved"
        }

    # Rule R2: Opened item returned within 30 calendar days (80% refund)
    if days_since_purchase <= 30 and clean_condition == "opened":
        # EF-04: Rounding must never exceed 80% ceiling or original amount paid
        max_allowed = float(amount_paid) * 0.8
        refund_val = min(round(max_allowed, 2), max_allowed)
        return {
            "refund": refund_val,
            "currency": "USD",
            "rule_id": "R2",
            "status": "approved"
        }

    # Rule R3: Return requested after 30 calendar days (expired)
    if days_since_purchase > 30:
        return {
            "refund": 0.0,
            "currency": "USD",
            "rule_id": "R3",
            "status": "expired"
        }

    # Default fallback for unrecognized item condition
    return {
        "refund": 0.0,
        "currency": "USD",
        "rule_id": "REJECTED_CONDITION",
        "status": "rejected"
    }
