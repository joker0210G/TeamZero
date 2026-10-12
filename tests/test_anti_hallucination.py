"""Unit tests for Anti-Hallucination, Semantic Grounding, and Neurosymbolic Guardrails Engine."""

from pathlib import Path
import pytest

from teamzero.anti_hallucination import (
    rank_tools,
    NeurosymbolicValidator,
    validate_code_grounding,
    surface_assumptions,
    multiagent_cross_validate
)


def test_semantic_tool_selection():
    available_tools = [
        {"name": "teamzero_run_gauntlet", "description": "Runs deterministic merge verification gates."},
        {"name": "teamzero_read_symbol", "description": "Extracts only target function or class via AST."},
        {"name": "teamzero_ideate_spec", "description": "Compiles Design Thinking Ask markdown to spec."},
        {"name": "teamzero_check_merge", "description": "Evaluates HMAC receipts and merge eligibility."}
    ]

    # Query targeting AST reading
    ranked1 = rank_tools("inspect class function syntax", available_tools, top_k=2)
    assert len(ranked1) == 2
    assert ranked1[0]["name"] == "teamzero_read_symbol"

    # Query targeting merge verification
    ranked2 = rank_tools("verify gauntlet and check merge", available_tools, top_k=2)
    top_names = [t["name"] for t in ranked2]
    assert "teamzero_run_gauntlet" in top_names or "teamzero_check_merge" in top_names


def test_neurosymbolic_guardrails(tmp_path):
    validator = NeurosymbolicValidator(root=tmp_path)

    # 1. Complexity boundary rule
    passed, viol = validator.validate_tool_call("teamzero_add_task", {"complexity": 15})
    assert not passed
    assert viol is not None
    assert viol.rule_id == "R02_COMPLEXITY_RANGE"

    # 2. Secret file access rule
    passed, viol = validator.validate_tool_call("any_tool", {"file_path": ".teamzero/.mintkey"})
    assert not passed
    assert viol is not None
    assert viol.rule_id == "R01_SECRET_ACCESS"

    # 3. Path traversal escape rule
    passed, viol = validator.validate_tool_call("any_tool", {"file_path": "../../etc/passwd"})
    assert not passed
    assert viol is not None
    assert viol.rule_id == "R01_PATH_ESCAPE"

    # 4. Empty identifier rule
    passed, viol = validator.validate_tool_call("teamzero_get_task", {"task_id": "   "})
    assert not passed
    assert viol is not None
    assert viol.rule_id == "R03_EMPTY_IDENTIFIER"

    # 5. Valid call
    passed, viol = validator.validate_tool_call("teamzero_add_task", {"task_id": "TASK-01", "complexity": 4})
    assert passed
    assert viol is None


def test_ast_code_grounding(tmp_path):
    # Case 1: Fabricated module
    fake_code = "from teamzero.quantum_crypto_engine import super_encrypt\nsuper_encrypt()"
    res1 = validate_code_grounding(fake_code, root=tmp_path)
    assert not res1["grounded"]
    assert res1["findings"][0]["kind"] == "FABRICATED_MODULE"

    # Case 2: Real module with fabricated symbol
    fake_sym_code = "from teamzero.config import NON_EXISTENT_MAGIC_VARIABLE_999\nprint(1)"
    res2 = validate_code_grounding(fake_sym_code)
    assert not res2["grounded"]
    assert res2["findings"][0]["kind"] == "MISSING_SYMBOL"
    assert "NON_EXISTENT_MAGIC_VARIABLE_999" in res2["findings"][0]["symbol"]

    # Case 3: Grounded real code
    real_code = "from teamzero.config import ROOT_DIR\nprint(ROOT_DIR)"
    res3 = validate_code_grounding(real_code)
    assert res3["grounded"]
    assert res3["total_findings"] == 0


def test_surface_assumptions():
    brief = "Build a payment processing endpoint that takes user currency and charges their card."
    report = surface_assumptions(brief)

    assert "stated_assumptions" in report
    assert "ambiguities_flagged" in report
    assert "missing_edge_cases" in report
    assert "clarifying_questions" in report
    assert "uncertainty_policy" in report
    assert "Permission granted to say 'I don't know'" in report["uncertainty_policy"]


def test_multiagent_cross_validation():
    # Candidate with hardcoded API key (Critic should reject)
    secret_code = "from teamzero.config import ROOT_DIR\napi_key = 'abcdef1234567890abcdef123456'\n"
    verdict1 = multiagent_cross_validate(secret_code)
    assert verdict1.status == "REJECTED"
    assert any("INV-04" in r for r in verdict1.reasons)

    # Clean candidate
    clean_code = "from teamzero.config import ROOT_DIR\ndef run(): return str(ROOT_DIR)\n"
    verdict2 = multiagent_cross_validate(clean_code)
    assert verdict2.status == "APPROVED"
