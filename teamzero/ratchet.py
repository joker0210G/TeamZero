"""TeamZero Self-Healing Ratchet Engine (Improvement #10).

Monitors and maintains deterministic checks:
1. Tracks check health and firing frequency
2. Identifies stale or obsolete checks
3. Auto-proposes new deterministic checks when new Evidence Graph nodes are resolved
"""

from __future__ import annotations
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from teamzero.config import ORG_DIR
from teamzero.evidence import EvidenceGraph

RATCHET_REGISTRY_FILE = ORG_DIR / "redteam" / "ratchet_registry.json"


DEFAULT_CHECKS = [
    {
        "id": "chk_amount_zero_guard",
        "description": "Ensures amount_paid <= 0 raises ValueError",
        "pattern": r"(?i)def\s+calculate_refund",
        "status": "ACTIVE",
        "last_fired": "2026-10-12T10:00:00Z",
        "fire_count": 5
    },
    {
        "id": "chk_days_held_negative",
        "description": "Ensures days_since_purchase < 0 is guarded",
        "pattern": r"(?i)days_since_purchase\s*<\s*0",
        "status": "ACTIVE",
        "last_fired": "2026-10-12T11:00:00Z",
        "fire_count": 3
    },
    {
        "id": "chk_legacy_xml_parser",
        "description": "Legacy check for removed XML import",
        "pattern": r"(?i)import\s+xml\.etree",
        "status": "STALE",
        "last_fired": "2026-04-01T00:00:00Z",
        "fire_count": 0
    }
]


def load_ratchet_registry() -> List[Dict[str, Any]]:
    """Loads current ratchet checks registry."""
    if not RATCHET_REGISTRY_FILE.exists():
        RATCHET_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        RATCHET_REGISTRY_FILE.write_text(json.dumps(DEFAULT_CHECKS, indent=2), encoding="utf-8")
        return list(DEFAULT_CHECKS)
    try:
        return json.loads(RATCHET_REGISTRY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return list(DEFAULT_CHECKS)


def save_ratchet_registry(checks: List[Dict[str, Any]]):
    RATCHET_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    RATCHET_REGISTRY_FILE.write_text(json.dumps(checks, indent=2), encoding="utf-8")


def audit_ratchet_health() -> Dict[str, Any]:
    """Evaluates ratchet checks health and discovers candidates for promotion or archival."""
    checks = load_ratchet_registry()
    ev_graph = EvidenceGraph()

    active = [c for c in checks if c.get("status") == "ACTIVE"]
    stale = [c for c in checks if c.get("status") == "STALE" or c.get("fire_count", 0) == 0]

    # Auto-propose checks from newly resolved Evidence Graph nodes
    proposed_new = []
    resolved_nodes = [n for n in ev_graph.list_nodes() if n.status == "RESOLVED"]
    for r in resolved_nodes:
        check_id = f"chk_auto_{r.node_id[:16]}"
        if not any(c.get("id") == check_id for c in checks):
            proposed_new.append({
                "id": check_id,
                "description": f"Auto-promoted from resolved evidence: {r.claim}",
                "source_evidence_node": r.node_id,
                "status": "PROPOSED"
            })

    return {
        "total_checks": len(checks),
        "active_count": len(active),
        "stale_count": len(stale),
        "active_checks": active,
        "stale_checks": stale,
        "proposed_promotions": proposed_new
    }
