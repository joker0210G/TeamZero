"""Unit test suite for refund_service adhering to QA invariants.
Author: QA Agent (derived from SPEC-REFUND-001)
"""

import pytest
from teamzero.refund_service import calculate_refund


def test_r1_unopened_within_30_days_receives_full_refund():
    # Day 0
    res0 = calculate_refund(100.0, 0, "unopened")
    assert res0["refund"] == 100.0
    assert res0["rule_id"] == "R1"
    
    # Day 15
    res15 = calculate_refund(50.25, 15, "unopened")
    assert res15["refund"] == 50.25
    assert res15["rule_id"] == "R1"

    # Day 30 exact boundary
    res30 = calculate_refund(200.0, 30, "unopened")
    assert res30["refund"] == 200.0
    assert res30["rule_id"] == "R1"


def test_r2_opened_within_30_days_receives_80_percent_refund():
    res10 = calculate_refund(100.0, 10, "opened")
    assert res10["refund"] == 80.0
    assert res10["rule_id"] == "R2"

    # Boundary day 30
    res30 = calculate_refund(50.0, 30, "opened")
    assert res30["refund"] == 40.0
    assert res30["rule_id"] == "R2"


def test_r3_past_30_days_receives_zero():
    res31 = calculate_refund(100.0, 31, "unopened")
    assert res31["refund"] == 0.0
    assert res31["rule_id"] == "R3"

    res60 = calculate_refund(100.0, 60, "opened")
    assert res60["refund"] == 0.0
    assert res60["rule_id"] == "R3"


def test_unguarded_negative_inputs_raise_value_error():
    with pytest.raises(ValueError, match="amount_paid cannot be negative"):
        calculate_refund(-10.0, 5, "unopened")

    with pytest.raises(ValueError, match="days_since_purchase cannot be negative"):
        calculate_refund(100.0, -1, "unopened")


def test_invalid_types_raise_type_error():
    with pytest.raises(TypeError):
        calculate_refund("100", 5, "unopened")

    with pytest.raises(TypeError):
        calculate_refund(100.0, "5", "unopened")


def test_case_insensitivity_and_whitespace():
    res = calculate_refund(100.0, 10, "  UNOPENED  ")
    assert res["refund"] == 100.0
    assert res["rule_id"] == "R1"
