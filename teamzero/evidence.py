"""TeamZero Typed Evidence Graph Engine.

Instead of treating experiments and testing outcomes as transient pass/fail events,
TeamZero captures findings as typed evidence nodes with persistent lineage.

Key Capabilities:
1. Typed nodes: BOUNDARY_MISS, SEMANTIC_MUTATION, LLM_PROBE, DETERMINISTIC_PASS, SPEC_VIOLATION.
2. Querying past evidence to skip redundant probes (token & CPU economy).
3. Detecting recurrence of known bugs (enabling evidence-weighted trust decay).
4. Checking for unresolved HIGH/CRITICAL nodes blocking merge.
"""

from __future__ import annotations
import hashlib
import json
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from teamzero.config import EVIDENCE_DIR


@dataclass
class EvidenceNode:
    node_id: str
    task_id: str
    generation: int
    type: str  # BOUNDARY_MISS | SEMANTIC_MUTATION | LLM_PROBE | DETERMINISTIC_PASS | SPEC_VIOLATION
    claim: str
    evidence: str
    severity: str  # CRITICAL | HIGH | MEDIUM | LOW
    status: str = "OPEN"  # OPEN | RESOLVED | INHERITED
    repro: str = ""
    commit_sha: str = ""
    parent_node_ids: List[str] = field(default_factory=list)
    resolved_by_commit: Optional[str] = None
    cost_tokens: int = 0
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EvidenceNode:
        return cls(
            node_id=data["node_id"],
            task_id=data.get("task_id", ""),
            generation=data.get("generation", 1),
            type=data.get("type", "BOUNDARY_MISS"),
            claim=data.get("claim", ""),
            evidence=data.get("evidence", ""),
            severity=data.get("severity", "MEDIUM").upper(),
            status=data.get("status", "OPEN").upper(),
            repro=data.get("repro", ""),
            commit_sha=data.get("commit_sha", ""),
            parent_node_ids=data.get("parent_node_ids", []),
            resolved_by_commit=data.get("resolved_by_commit"),
            cost_tokens=data.get("cost_tokens", 0),
            created_at=data.get("created_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        )


class EvidenceGraph:
    """Manages reading, querying, and updating the local Typed Evidence Graph."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or EVIDENCE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def record_finding(
        self,
        task_id: str,
        commit_sha: str,
        generation: int,
        finding_dict: Dict[str, Any],
        cost_tokens: int = 0
    ) -> EvidenceNode:
        """Converts a Breaker Finding into a persistent typed EvidenceNode."""
        sev = finding_dict.get("severity", "MEDIUM").upper()
        phase = finding_dict.get("phase", "UNKNOWN").upper()
        title = finding_dict.get("title", "")
        evidence_str = finding_dict.get("evidence", "")
        repro_str = finding_dict.get("repro", "")

        # Map phase to evidence type
        type_map = {
            "PHASE_A": "SPEC_VIOLATION",
            "PHASE_B": "BOUNDARY_MISS",
            "PHASE_C": "SEMANTIC_MUTATION",
            "PHASE_D": "LLM_PROBE"
        }
        ev_type = type_map.get(phase, "BOUNDARY_MISS")

        # Deterministic node ID based on content
        content_hash = hashlib.sha256(f"{task_id}:{title}:{evidence_str}".encode()).hexdigest()[:8]
        node_id = f"ev-{task_id[:16]}-{content_hash}"

        # Check if an existing node with this ID or similar claim exists
        existing = self.get_node(node_id)
        parent_ids = []
        if existing:
            parent_ids.append(existing.node_id)

        node = EvidenceNode(
            node_id=node_id,
            task_id=task_id,
            generation=generation,
            type=ev_type,
            claim=title,
            evidence=evidence_str,
            severity=sev,
            status="OPEN",
            repro=repro_str,
            commit_sha=commit_sha,
            parent_node_ids=parent_ids,
            cost_tokens=cost_tokens
        )
        self.save_node(node)
        return node

    def save_node(self, node: EvidenceNode):
        path = self.storage_dir / f"{node.node_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(node.to_dict(), f, indent=2)

    def get_node(self, node_id: str) -> Optional[EvidenceNode]:
        path = self.storage_dir / f"{node_id}.json"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return EvidenceNode.from_dict(json.load(f))
        except Exception:
            return None

    def list_nodes(self, task_id: Optional[str] = None, status: Optional[str] = None) -> List[EvidenceNode]:
        nodes = []
        for p in self.storage_dir.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    node = EvidenceNode.from_dict(json.load(f))
                    if task_id and node.task_id != task_id:
                        continue
                    if status and node.status != status.upper():
                        continue
                    nodes.append(node)
            except Exception:
                continue
        return sorted(nodes, key=lambda n: n.created_at)

    def has_similar_finding(self, claim_or_evidence: str) -> bool:
        """Checks if a matching or very similar claim/evidence was previously recorded."""
        norm_query = claim_or_evidence.lower().strip()
        for node in self.list_nodes():
            if norm_query in node.claim.lower() or norm_query in node.evidence.lower():
                return True
        return False

    def mark_resolved(self, node_id: str, resolved_by_commit: str):
        node = self.get_node(node_id)
        if node:
            node.status = "RESOLVED"
            node.resolved_by_commit = resolved_by_commit
            self.save_node(node)

    def get_unresolved_critical_or_high(self, task_id: Optional[str] = None) -> List[EvidenceNode]:
        """Returns any open CRITICAL or HIGH nodes blocking merge safety."""
        unresolved = []
        for node in self.list_nodes(task_id=task_id, status="OPEN"):
            if node.severity in ("CRITICAL", "HIGH"):
                unresolved.append(node)
        return unresolved
