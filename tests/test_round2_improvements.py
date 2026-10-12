"""Unit and integration tests for TeamZero Round 2 Improvements.

Covers:
- Event Journal & Time Travel Debugger
- Pareto Scoreboard & Dominance
- Solution Diversity Niche Classification
- Multi-Provider Model Router & Custom Configuration
- Adaptive Catch-up Trigger Engine
- AI Red-Team Adversarial Spec Mutation Engine
- Living SLA Dashboard & Breach Tracking
- XZ-Grade Supply Chain & Binary Fixture Auditing
- Automated Peer Review PR Draft Generator
"""

import json
from pathlib import Path
import pytest

from teamzero.journal import EventJournal
from teamzero.debugger import TimeTravelDebugger
from teamzero.pareto import SolutionCandidate, dominates, compute_pareto_front
from teamzero.diversity import classify_behavioral_niche, enforce_diversity_quota
from teamzero.model_router import ModelRouter
from teamzero.triggers import AdaptiveTriggerEngine
from teamzero.mutation import RedTeamMutationEngine
from teamzero.health import SLADashboard
from teamzero.supply_chain import SupplyChainScanner
from teamzero.peer_review import PeerReviewBot, ReviewComment


def test_event_journal_and_time_travel(tmp_path):
    journal = EventJournal("TEST-RUN-01", journal_dir=tmp_path)
    e1 = journal.emit("task_started", {"task_id": "T-100"})
    e2 = journal.emit("finding_logged", {"severity": "CRITICAL", "rule": "NO_LEAK"})
    e3 = journal.emit("trust_updated", {"peer": "agent_alpha", "delta": -0.2})

    assert e1.seq == 1
    assert e3.seq == 3

    summary = journal.replay_summary()
    assert summary["total_events"] == 3
    assert summary["last_seq"] == 3

    # Time-travel rewind to seq 2
    debugger = TimeTravelDebugger("TEST-RUN-01")
    debugger.journal = journal
    snap = debugger.rewind_to(2)
    assert snap.events_replayed == 2
    assert len(snap.reconstructed_state["findings"]) == 1
    assert "agent_alpha" not in snap.reconstructed_state["trust_deltas"]


def test_pareto_scoreboard_dominance():
    c1 = SolutionCandidate("A", {"speed": 100.0, "coverage": 90.0}, {})
    c2 = SolutionCandidate("B", {"speed": 80.0, "coverage": 80.0}, {})
    c3 = SolutionCandidate("C", {"speed": 70.0, "coverage": 95.0}, {})

    metrics = ["speed", "coverage"]
    # c1 strictly dominates c2
    assert dominates(c1, c2, metrics) is True
    # c1 does not dominate c3 because c3 has higher coverage (95 vs 90)
    assert dominates(c1, c3, metrics) is False

    front = compute_pareto_front([c1, c2, c3], metrics)
    ids = [c.candidate_id for c in front]
    assert "A" in ids
    assert "C" in ids
    assert "B" not in ids  # Dominated


def test_solution_diversity_guard():
    code_defensive = "def check(x):\n    if not x:\n        raise ValueError('empty')\n"
    code_optimistic = "def run():\n    try:\n        do_work()\n    except Exception as e:\n        log(e)\n"

    assert classify_behavioral_niche(code_defensive) == "validation_first"
    assert classify_behavioral_niche(code_optimistic) == "optimistic_resilient"

    candidates = [
        {"id": "1", "code": code_defensive},
        {"id": "2", "code": code_optimistic},
    ]
    niches = enforce_diversity_quota(candidates)
    assert len(niches) >= 2


def test_model_router_custom_provider(tmp_path):
    cfg_file = tmp_path / "providers.yaml"
    router = ModelRouter(config_path=cfg_file)

    # Default tier assignments
    assert router.resolve_tier("audit", severity="CRITICAL") == "frontier"
    assert router.resolve_tier("lint", severity="LOW") == "lite"

    # User reconfigures frontier tier to local ollama model
    router.set_tier_model("frontier", provider="ollama", model="qwen2.5-coder")
    target = router.get_tier_target("frontier")
    assert target["provider"] == "ollama"
    assert target["model"] == "qwen2.5-coder"


def test_adaptive_trigger_engine_missed_run(tmp_path):
    engine = AdaptiveTriggerEngine(triggers_dir=tmp_path)
    # Simulate a trigger whose last run was 48 hours ago
    engine.state["daily_audit"] = 1000.0
    now = 1000.0 + 86400.0 + 5000.0  # overdue

    statuses = engine.evaluate_triggers(current_time=now)
    audit_status = next(s for s in statuses if s.trigger_id == "daily_audit")
    assert audit_status.status == "MISSED_OVERDUE"


def test_red_team_adversarial_mutation():
    engine = RedTeamMutationEngine()
    sample_code = """
def process_refund(amount):
    if amount <= 0:
        raise ValueError("Invalid amount")
    return float(amount)
"""
    mutants = engine.generate_adversarial_mutants(sample_code)
    assert len(mutants) >= 2

    # Evaluator catches boundary mutants but lets precision mutants pass
    def mock_evaluator(code):
        if "int(amount)" in code:
            return True  # Survived!
        return False  # Caught!

    res = engine.evaluate_spec_resilience(mutants, mock_evaluator)
    assert res.total_mutants > 0
    assert len(res.blind_spots) > 0


def test_living_sla_dashboard(tmp_path):
    health_file = tmp_path / "health.json"
    dash = SLADashboard(health_file=health_file)
    rep = dash.compute_health()
    assert rep.overall_status in ["HEALTHY", "WARNING", "CRITICAL_BREACH"]
    assert health_file.exists()


def test_supply_chain_xz_binary_detection(tmp_path):
    scanner = SupplyChainScanner(root_dir=tmp_path)
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(parents=True)

    # Inject hidden shell payload into a binary test fixture file (XZ attack pattern)
    bad_fixture = tests_dir / "sample_data.bin"
    bad_fixture.write_bytes(b"\x00\x01\x02#!/bin/sh\neval payload\x00")

    risks = scanner.scan_hidden_test_payloads()
    assert len(risks) == 1
    assert risks[0].risk_id == "XZ_SUSPICIOUS_BINARY_TEST_PAYLOAD"
    assert risks[0].severity == "CRITICAL"

    # Typosquat check
    typo_risks = scanner.check_typosquatting(["reqeusts", "fastapi"])
    assert any(r.risk_id == "POSSIBLE_TYPOSQUAT_DEPENDENCY" for r in typo_risks)


def test_peer_review_bot(tmp_path):
    bot = PeerReviewBot(decisions_dir=tmp_path)
    comments = [
        ReviewComment(
            file_path="teamzero/core.py",
            line_number=10,
            rule="NO_HARDCODED_KEYS",
            severity="CRITICAL",
            message="Possible secret token in source string.",
            suggested_fix="os.environ.get('SECRET')",
        )
    ]
    out = bot.generate_review_markdown("feat/test", "main", comments)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "CHANGES REQUESTED" in content
    assert "NO_HARDCODED_KEYS" in content
