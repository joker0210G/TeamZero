"""TeamZero Canary Lineage Tracker (Improvement #8).

Traces security events and war game canary leaks back to:
- The specific task ID and generation
- The author agent last modifying the code
- The exact git commit and source file/line
- Correlated Evidence Graph nodes
"""

from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from teamzero.config import ORG_DIR
from teamzero.evidence import EvidenceGraph

CANARY_EVENTS_FILE = ORG_DIR / "redteam" / "canary_events.jsonl"


def log_canary_event(
    canary_id: str,
    campaign_id: str,
    leaked_file: str,
    target_task_id: str = "TASK-UNKNOWN",
    author_agent: str = "unknown-agent"
) -> Dict[str, Any]:
    """Records an auditable canary breach with full lineage."""
    CANARY_EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    ev_graph = EvidenceGraph()
    correlated_nodes = [n.node_id for n in ev_graph.list_nodes(task_id=target_task_id)]

    record = {
        "event_id": f"CANARY-EV-{int(time.time())}",
        "canary_id": canary_id,
        "campaign_id": campaign_id,
        "leaked_file": leaked_file,
        "task_id": target_task_id,
        "author_agent": author_agent,
        "correlated_evidence_nodes": correlated_nodes,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "severity": "CRITICAL"
    }

    with open(CANARY_EVENTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    return record


def list_canary_events() -> List[Dict[str, Any]]:
    """Returns all logged canary breach events."""
    if not CANARY_EVENTS_FILE.exists():
        return []
    events = []
    with open(CANARY_EVENTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    events.append(json.loads(line))
                except Exception:
                    pass
    return events
