# Module Card: Refund Service (`teamzero.refund_service`)

## Purpose
Calculates customer refunds based on days elapsed since purchase, item condition, and original amount paid.

## Public Interface
- `calculate_refund(amount_paid: float, days_since_purchase: int, item_condition: str) -> dict`
  - Returns: `{"refund": float, "currency": str, "rule_id": str}`

## Decision Table Rules
- **R1**: `days_since_purchase <= 30` AND `item_condition == "unopened"` => `1.0 * amount_paid` (Full refund)
- **R2**: `days_since_purchase <= 30` AND `item_condition == "opened"` => `0.8 * amount_paid` (80% restocking deduction)
- **R3**: `days_since_purchase > 30` => `0.0` (Expired)

## Invariants
1. `0.0 <= refund <= amount_paid` for all `amount_paid >= 0.0`.
2. `amount_paid < 0.0` or `days_since_purchase < 0` must raise `ValueError` (guarded inputs).
3. The returned `refund` value must be a finite float rounded to 2 decimal places.

## Known Traps
- **Boundary Slip**: Using `< 30` instead of `<= 30` returns 0.0 on exactly day 30.
- **Unguarded Negative Inputs**: Failing to guard `amount_paid < 0` or negative days can result in negative refunds or fraudulent payouts.
- **Floating Point Imprecision**: Failing to use `round(val, 2)` can cause decimal noise in downstream ledger records.
