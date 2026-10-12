import json
import pytest
from pathlib import Path
from teamzero.evidence import EvidenceGraph, EvidenceNode
from teamzero.merge_gate import evaluate_merge_prerequisites
from teamzero.governance import sign_receipt


def test_evidence_graph_record_and_query(tmp_path):
    graph = EvidenceGraph(storage_dir=tmp_path)
    finding = {
        "phase": "PHASE_B",
        "severity": "CRITICAL",
        "title": "Invariant Violation: amount < 0",
        "evidence": "amount_paid=-10.0 accepted",
        "repro": "calc(-10.0)"
    }
    node = graph.record_finding("TASK-UNIT-001", "commit123", generation=1, finding_dict=finding)
    assert node.status == "OPEN"
    assert node.type == "BOUNDARY_MISS"
    assert node.severity == "CRITICAL"

    nodes = graph.list_nodes(task_id="TASK-UNIT-001")
    assert len(nodes) == 1
    assert nodes[0].node_id == node.node_id

    # Test query
    assert graph.has_similar_finding("amount_paid=-10.0")
    assert not graph.has_similar_finding("unrelated_foo_bar")

    # Test resolution
    graph.mark_resolved(node.node_id, resolved_by_commit="commit456")
    updated = graph.get_node(node.node_id)
    assert updated.status == "RESOLVED"
    assert updated.resolved_by_commit == "commit456"

    # Check unresolved critical/high
    unresolved = graph.get_unresolved_critical_or_high(task_id="TASK-UNIT-001")
    assert len(unresolved) == 0


def test_merge_gate_blocks_on_open_critical_evidence(tmp_path, monkeypatch):
    from teamzero.config import FINDINGS_DIR
    FINDINGS_DIR.mkdir(parents=True, exist_ok=True)
    test_sha = "deadbeef11223344556677889900aabbccddeeff"
    short_sha = test_sha[:8]
    task_id = "TASK-EVIDENCE-BLOCK-001"

    # Create findings packet indicating PASS from breaker
    packet_path = FINDINGS_DIR / f"{task_id}_{short_sha}.json"
    packet_path.write_text(json.dumps({
        "task_id": task_id,
        "commit_sha": test_sha,
        "verdict": "PASS",
        "summary": {"critical": 0, "high": 0}
    }), encoding="utf-8")

    # Record an open CRITICAL evidence node for this task
    graph = EvidenceGraph()
    node = graph.record_finding(
        task_id=task_id,
        commit_sha=test_sha,
        generation=1,
        finding_dict={
            "phase": "PHASE_B",
            "severity": "CRITICAL",
            "title": "Known lingering defect",
            "evidence": "Must block merge until resolved"
        }
    )

    try:
        sign_receipt(f"gauntlet_run:{test_sha}", "gauntlet_run")
        sign_receipt(f"{task_id}:{test_sha}", "breaker_run")
        sign_receipt(f"founder_approval:{test_sha}", "founder_approval")

        res = evaluate_merge_prerequisites(target_ref=test_sha, required_autonomy_level=2)
        # Should be blocked specifically by evidence graph!
        assert not res["eligible_to_merge"]
        assert not res["gates"]["evidence_graph"]["passed"]
        assert res["gates"]["evidence_graph"]["unresolved_critical_high"] == 1

        # Now mark resolved
        graph.mark_resolved(node.node_id, resolved_by_commit=test_sha)
        res_after = evaluate_merge_prerequisites(target_ref=test_sha, required_autonomy_level=2)
        assert res_after["gates"]["evidence_graph"]["passed"]
        assert res_after["eligible_to_merge"]
    finally:
        if packet_path.exists():
            packet_path.unlink()
        node_file = graph.storage_dir / f"{node.node_id}.json"
        if node_file.exists():
            node_file.unlink()
