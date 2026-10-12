"""Unit tests for Chain-of-Verification (CoVe) and Self-Consistency Engine."""

from pathlib import Path
import pytest

from teamzero.cove import (
    generate_verification_plan,
    execute_verification_plan,
    rectify_and_revise,
    run_chain_of_verification,
    compute_self_consistency,
    VerificationQuestion,
    VerificationAnswer
)


def test_generate_verification_plan():
    code = "def add(a: int, b: int) -> int: return a + b"
    plan = generate_verification_plan(code, feature="math")
    assert len(plan) == 5
    categories = [q.category for q in plan]
    assert "SYNTAX_VALIDITY" in categories
    assert "API_GROUNDING" in categories
    assert "INVARIANT_CHECK" in categories
    assert "TRAP_COMPLIANCE" in categories
    assert "BOUNDARY_EDGE" in categories


def test_execute_verification_plan():
    # Clean code with boundary check
    clean_code = """from teamzero.config import ROOT_DIR

def get_path(sub: str) -> str:
    if not sub:
        raise ValueError("Empty subpath")
    return str(ROOT_DIR / sub)
"""
    plan = generate_verification_plan(clean_code)
    answers = execute_verification_plan(clean_code, plan)
    assert len(answers) == 5
    assert all(a.verified for a in answers)


def test_cove_hallucination_detection_and_rectification():
    # Code with hardcoded secret and missing symbol
    buggy_code = """from teamzero.config import ROOT_DIR
api_key = 'abcdef1234567890abcdef123456'

def compute(x: int) -> int:
    if x < 0:
        return 0
    return x * 2
"""
    result = run_chain_of_verification(buggy_code)
    # The hardcoded secret should be caught and rectified
    assert len(result["corrections_applied"]) > 0
    assert "os.environ.get" in result["revised_code"]
    assert "abcdef1234567890abcdef123456" not in result["revised_code"]


def test_self_consistency_consensus():
    c1 = """def solve(n: int) -> int:
    if n <= 1: return 1
    return n * solve(n - 1)
"""
    c2 = """def solve(n: int) -> int:
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
"""
    c3 = """def completely_different_thing():
    pass
"""
    res = compute_self_consistency([c1, c2, c3])
    assert res["status"] == "CONSENSUS_REACHED"
    assert res["consensus_score"] >= 0.6
    assert "solve" in res["shared_symbols"]
