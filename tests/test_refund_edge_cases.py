"""Edge-case test battery for SPEC-REFUND-001 (teamzero.refund_service).

Author: QA Agent - derived from SPEC-REFUND-001 only (Constitution INV-02).
Target: tests/test_refund_edge_cases.py

SECTION MAP
  Part 1 - Spec-derived boundary sweep ........... expected GREEN today
  Part 2 - Invariant fuzz (finite inputs) .......... expected GREEN today
  Part 3 - Non-finite inputs (NaN / inf) ........... expected RED  (finding EF-01/02)
  Part 4 - Bool subclass smuggling ................. expected RED  (finding EF-03)
  Part 5 - Rounding over-refund .................... expected RED  (finding EF-04)
  Part 6 - Condition-string adversarial inputs ..... expected GREEN today

RED tests assert the CORRECT behavior. They are L1 Breaker findings: the
implementation is guilty until these pass. Do not weaken the assertion -
fix refund_service.py (guard with math.isfinite, reject bool, clamp refund
to amount_paid with Decimal quantize ROUND_HALF_UP).
"""

import math
import random

import pytest

from teamzero.refund_service import calculate_refund


# ---------------------------------------------------------------------------
# Part 1 - Spec-derived boundary sweep (decision table, not the diff)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("days,condition,expected_rule,expected_refund", [
    (0,  "unopened", "R1", 100.0),
    (1,  "unopened", "R1", 100.0),
    (29, "unopened", "R1", 100.0),
    (30, "unopened", "R1", 100.0),   # exact boundary: <= 30 must hold
    (31, "unopened", "R3", 0.0),     # one past boundary: must flip
    (30, "opened",   "R2", 80.0),
    (31, "opened",   "R3", 0.0),
    (365, "unopened", "R3", 0.0),
    (0,  "opened",   "R2", 80.0),
    (0,  "damaged",  "REJECTED_CONDITION", 0.0),
])
def test_spec_boundary_sweep(days, condition, expected_rule, expected_refund):
    res = calculate_refund(100.0, days, condition)
    assert res["rule_id"] == expected_rule
    assert res["refund"] == expected_refund


def test_condition_normalization_variants():
    for raw in ["unopened", "UNOPENED", "  UnOpened  ", "unopened\t"]:
        assert calculate_refund(10.0, 5, raw)["rule_id"] == "R1"


# ---------------------------------------------------------------------------
# Part 2 - Invariant fuzz (finite inputs only)
# ---------------------------------------------------------------------------

def test_invariant_fuzz_finite_inputs():
    rng = random.Random(20261012)  # deterministic seed, reproducible CI
    for _ in range(2000):
        amount = round(rng.uniform(0.10, 5000.00), 2)  # valid money, 2dp
        days = rng.randint(0, 365)
        condition = rng.choice(["unopened", "opened"])
        res = calculate_refund(amount, days, condition)
        assert res["refund"] >= 0.0, f"negative refund: {res}"
        assert res["refund"] <= amount, f"over-refund: {res} for amount {amount}"
        assert isinstance(res["refund"], (int, float))
        assert not isinstance(res["refund"], bool)


# ---------------------------------------------------------------------------
# Part 3 - Non-finite inputs  (EF-01: NaN, EF-02: inf)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [float("nan"), float("-nan"), float("inf"), float("-inf")])
def test_nonfinite_amount_must_raise(bad):
    with pytest.raises((ValueError, TypeError)):
        calculate_refund(bad, 5, "unopened")


# ---------------------------------------------------------------------------
# Part 4 - Bool subclass smuggling  (EF-03)
# ---------------------------------------------------------------------------

def test_bool_days_rejected():
    with pytest.raises(TypeError):
        calculate_refund(100.0, True, "unopened")   # True == 1 day, silently passes today


def test_bool_amount_rejected():
    with pytest.raises(TypeError):
        calculate_refund(True, 5, "unopened")       # True == $1.00, silently passes today


# ---------------------------------------------------------------------------
# Part 5 - Rounding must never refund more than paid  (EF-04)
# ---------------------------------------------------------------------------

def test_rounding_cannot_exceed_amount_unopened():
    # round(99.999, 2) == 100.0 -> over-refund of $0.001 today
    res = calculate_refund(99.999, 0, "unopened")
    assert res["refund"] <= 99.999


def test_rounding_cannot_exceed_amount_opened():
    res = calculate_refund(99.999, 10, "opened")
    assert res["refund"] <= 99.999 * 0.8 + 1e-9


def test_subcent_amount_opened():
    # spec is silent on < $0.01; invariant refund <= amount must still hold
    res = calculate_refund(0.005, 10, "opened")
    assert res["refund"] >= 0.0
    assert res["refund"] <= 0.005


# ---------------------------------------------------------------------------
# Part 6 - Condition-string adversarial inputs
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("weird", [
    "", " ", "null", "None", "0", "ünïcödé",
    "opened\x00",
    pytest.param("unopened" * 1000, id="long_unopened_8k"),
    "UNOPENED\u200b",
])
def test_weird_condition_strings_never_crash(weird):
    res = calculate_refund(50.0, 5, weird)
    assert res["rule_id"] in ("R1", "R2", "R3", "REJECTED_CONDITION")
    assert res["refund"] >= 0.0


def test_exactly_30_days_2359_boundary_semantics():
    # The spec counts calendar days as ints; 30 must be the LAST eligible day.
    assert calculate_refund(1.0, 30, "unopened")["rule_id"] == "R1"
    assert calculate_refund(1.0, 31, "unopened")["rule_id"] == "R3"


def test_zero_amount_is_approved_not_rejected():
    res = calculate_refund(0.0, 10, "unopened")
    assert res["rule_id"] == "R1"
    assert res["refund"] == 0.0
