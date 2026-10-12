"""TeamZero Hypothesis Racing Engine ( Parallel Research Peers).

Races multiple peer implementation strategies in parallel against the same spec:
- Peer A (Straightforward / Naive)
- Peer B (Defensive / Strict Guards)
- Peer C (Performance / Batch Optimized)

Evaluates each candidate via Gauntlet + Task Evaluator and selects the highest scoring winner.
"""

from __future__ import annotations
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

from teamzero.evaluator import evaluate_task_criteria


# ---------------------------------------------------------------------------
# DEMO REFERENCE CANDIDATES:
# When agents invoke `tz race`, real agents formulate independent branch diffs.
# The strategies below serve as an offline mock/demo test harness.
# ---------------------------------------------------------------------------
DEMO_REFERENCE_STRATEGIES = [
    {
        "id": "peer_naive",
        "name": "Peer A (Straightforward)",
        "code_template": r'''
def calculate_refund(amount_paid, days_since_purchase, item_condition):
    amt = float(amount_paid)
    days = int(days_since_purchase)
    cond = str(item_condition).strip().lower()
    if days <= 30 and cond == "unopened":
        return {"refund": round(amt * 1.0, 2), "rule_id": "R1"}
    elif days <= 30 and cond == "opened":
        return {"refund": round(amt * 0.8, 2), "rule_id": "R2"}
    return {"refund": 0.0, "rule_id": "R3"}
'''
    },
    {
        "id": "peer_defensive",
        "name": "Peer B (Defensive Strict)",
        "code_template": r'''
def calculate_refund(amount_paid, days_since_purchase, item_condition):
    if amount_paid is None or days_since_purchase is None or item_condition is None:
        raise ValueError("Parameters cannot be None")
    amt = float(amount_paid)
    days = int(days_since_purchase)
    if amt < 0.0 or days < 0:
        raise ValueError("amount_paid and days_since_purchase must be non-negative")
    cond = str(item_condition).strip().lower()
    if cond not in ("unopened", "opened"):
        raise ValueError(f"Invalid item_condition: {item_condition}")
    if days <= 30 and cond == "unopened":
        return {"refund": round(amt * 1.0, 2), "rule_id": "R1"}
    elif days <= 30 and cond == "opened":
        return {"refund": round(amt * 0.8, 2), "rule_id": "R2"}
    return {"refund": 0.0, "rule_id": "R3"}
'''
    },
    {
        "id": "peer_performance",
        "name": "Peer C (Fast Path)",
        "code_template": r'''
def calculate_refund(amount_paid, days_since_purchase, item_condition):
    amt = float(amount_paid)
    days = int(days_since_purchase)
    if amt < 0.0 or days < 0:
        raise ValueError("Invalid negative input")
    cond = str(item_condition).strip().lower()
    if days > 30:
        return {"refund": 0.0, "rule_id": "R3"}
    mult = 1.0 if cond == "unopened" else (0.8 if cond == "opened" else 0.0)
    return {"refund": round(amt * mult, 2), "rule_id": "R1" if cond == "unopened" else "R2"}
'''
    }
]


def race_peer_hypotheses(spec_path: Path, num_peers: int = 3) -> Dict[str, Any]:
    """Runs parallel peer hypotheses against the spec and determines the winner."""
    spec_data = json.loads(spec_path.read_text(encoding="utf-8"))
    selected_peers = DEMO_REFERENCE_STRATEGIES[:num_peers]

    results = []
    print(f"[*] Racing {len(selected_peers)} Research Peers against {spec_path.name}...")

    mod_name = spec_data.get("module", "")
    target_service_file = Path(mod_name.replace(".", "/") + ".py") if mod_name else Path("teamzero/refund_service.py")
    orig_code = target_service_file.read_text(encoding="utf-8") if target_service_file.exists() else ""

    try:
        for peer in selected_peers:
            pid = peer["id"]
            pname = peer["name"]
            print(f"    -> Evaluating {pname}...")

            # Temporarily apply candidate implementation
            target_service_file.write_text(peer["code_template"], encoding="utf-8")

            # Run evaluation
            eval_res = evaluate_task_criteria(
                spec_data=spec_data,
                candidate_entry={"file": str(target_service_file), "function": spec_data.get("function", "calculate_refund")},
                task_id=f"TASK-RACE-{pid}"
            )

            results.append({
                "peer_id": pid,
                "name": pname,
                "score": eval_res["composite_score"],
                "all_passed": eval_res["all_passed"],
                "details": eval_res["results"]
            })
    finally:
        # Restore original code
        if orig_code:
            target_service_file.write_text(orig_code, encoding="utf-8")

    # Pick winner with highest composite score
    sorted_peers = sorted(results, key=lambda x: x["score"], reverse=True)
    winner = sorted_peers[0]

    return {
        "spec_id": spec_data.get("spec_id", "UNKNOWN"),
        "peers_evaluated": len(results),
        "winner": winner,
        "leaderboard": sorted_peers
    }
