"""Unit tests for Sprint 1 & 2 Improvements (IMP-02, IMP-03, IMP-04, IMP-06)."""

import pytest
from pathlib import Path
from teamzero.tasks import TaskRegistry, MicroTask
from teamzero.cove import (
    run_selfcheck_verify,
    run_ever_verify,
    run_cove_rag_verify,
    run_ensemble_verification
)
from teamzero.anti_hallucination import find_cross_module_attack_chains
from teamzero.dynamic_gauntlet import DynamicGauntletRunner


def test_ai_task_crud_methods(tmp_path):
    reg_file = tmp_path / "tasks.json"
    reg = TaskRegistry(reg_file)

    # Test auto complexity scoring
    c1 = reg.auto_score_complexity(description="simple variable rename")
    c2 = reg.auto_score_complexity(description="critical cryptographic architecture refactor")
    assert c2 > c1

    # Add duplicate tasks
    t1 = reg.add_task("TASK-01", "Implement payment refund flow", "Handle refund requests and reversals")
    t2 = reg.add_task("TASK-02", "Implement payment refund flow", "Handle refund requests and reversals")
    assert len(reg.load_tasks()) == 2

    # Merge duplicates
    merge_res = reg.merge_duplicate_tasks(similarity_threshold=0.5)
    assert merge_res["merged_count"] == 1
    assert len(reg.load_tasks()) == 1

    # Reprioritize from breaker
    breaker_findings = [
        {"severity": "CRITICAL", "evidence": "payment refund token failure"}
    ]
    rep = reg.reprioritize_from_breaker(breaker_findings)
    assert rep["critical_files_detected"] == []


def test_cross_module_attack_chains():
    chains = find_cross_module_attack_chains()
    assert chains["status"] == "ANALYZED"
    assert "overall_cross_module_risk_score" in chains
    assert isinstance(chains["attack_chains"], list)


def test_multi_method_verification_ensemble():
    code = """
import os

def process_data(data):
    if not data:
        raise ValueError("Empty data")
    return str(data).strip()
"""
    # Test EVER
    ever_res = run_ever_verify(code)
    assert ever_res["status"] == "ATOMIC_VERIFIED"

    # Test SelfCheckGPT
    selfcheck_res = run_selfcheck_verify(code, [code, code])
    assert selfcheck_res["status"] == "VERIFIED_CONSISTENT"

    # Test Ensemble
    ens = run_ensemble_verification(code, [code])
    assert ens["ensemble_verdict"] == "VERIFIED_CLEAN"
    assert ens["composite_hallucination_risk"] <= 0.25


def test_dynamic_gauntlet_execution():
    runner = DynamicGauntletRunner()
    res = runner.execute_dynamic_gauntlet()
    assert res["status"] in ["GAUNTLET_PASS", "GAUNTLET_FAIL"]
    assert res["total_dynamic_tests"] >= 3
    assert "receipt" in res
