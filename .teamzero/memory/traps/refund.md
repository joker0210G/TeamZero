# Domain Traps: Refund Processing

## Trap 1: Off-By-One Operator Boundary
- **Pattern**: Developer writes `if days < 30:` instead of `if days <= 30:`.
- **Impact**: Customers returning items on exactly the 30th calendar day are erroneously rejected with 0 refund.
- **Probe**: Call `calculate_refund(100.0, 30, "unopened")`. Expected: `100.0`.

## Trap 2: Unguarded Negative Values
- **Pattern**: Developer omits validation on `amount_paid` or `days_since_purchase`.
- **Impact**: Supplying `amount_paid = -50.0` returns `refund = -50.0`, potentially draining customer account or executing unauthorized reverse transactions.
- **Probe**: Call with `amount_paid = -10.0` or `days = -1`. Expected: `ValueError`.

## Trap 3: Case-Sensitivity or Empty Strings
- **Pattern**: Exact string comparison `item_condition == "unopened"` without `.strip().lower()`.
- **Impact**: `"UNOPENED"` or `"unopened "` inadvertently triggers the opened/80% branch.
