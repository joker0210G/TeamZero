"""Refund calculation service for TeamZero.
Implements SPEC-REFUND-001 adhering to Quality Constitution invariants.
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
    if not isinstance(amount_paid, (int, float)):
        raise TypeError(f"amount_paid must be numeric, got {type(amount_paid).__name__}")
    if not isinstance(days_since_purchase, int):
        raise TypeError(f"days_since_purchase must be int, got {type(days_since_purchase).__name__}")
    if not isinstance(item_condition, str):
        raise TypeError(f"item_condition must be string, got {type(item_condition).__name__}")

    # Guard negative inputs (Prevents Traps 2)
    if amount_paid < 0.0:
        raise ValueError(f"amount_paid cannot be negative: {amount_paid}")
    if days_since_purchase < 0:
        raise ValueError(f"days_since_purchase cannot be negative: {days_since_purchase}")

    clean_condition = item_condition.strip().lower()

    # Rule R1: Unopened item returned within 30 calendar days (full refund)
    if days_since_purchase <= 30 and clean_condition == "unopened":
        refund_val = round(float(amount_paid), 2)
        return {
            "refund": refund_val,
            "currency": "USD",
            "rule_id": "R1",
            "status": "approved"
        }

    # Rule R2: Opened item returned within 30 calendar days (80% refund)
    if days_since_purchase <= 30 and clean_condition == "opened":
        refund_val = round(float(amount_paid) * 0.8, 2)
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
