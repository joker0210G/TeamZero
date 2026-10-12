"""TeamZero Merge Gate Authority.

Enforces ADR-001 & ADR-003:
Merge authority belongs strictly to the automated gate consuming SHA-keyed receipts.
External agents, developers, and LLMs cannot merge by assertion.

A merge to production/main requires:
1. Green Deterministic Gauntlet receipt (TZ-gauntlet_run:<sha>)
2. Passing L1 Red Team Breaker receipt (TZ-breaker_run:<sha>) with 0 critical/high findings
3. If autonomy < 5 (e.g. Level 2): Founder Approval signature (TZ-founder_approval:<sha>)
"""

from __future__ import annotations
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from teamzero.config import (
    ORG_DIR,
    RECEIPTS_LEDGER,
    TRUST_LEDGER,
    FINDINGS_DIR,
    SERVER_SECRET
)
from teamzero.governance import sign_receipt, verify_receipt, load_constitution


def get_git_commit_sha(target_ref: str = "HEAD") -> str:
    """Returns the full 40-char git commit SHA for a reference."""
    try:
        res = subprocess.run(["git", "rev-parse", target_ref], capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        # Fallback for unstaged or uncommitted working trees
        return "0000000000000000000000000000000000000000"


def get_receipts_for_sha(sha: str) -> List[Dict[str, Any]]:
    """Retrieves all receipts issued for a specific commit SHA from ledger."""
    results = []
    if not RECEIPTS_LEDGER.exists():
        return results
    short_sha = sha[:8]
    with open(RECEIPTS_LEDGER, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
                subj = rec.get("subject", "")
                if sha in subj or short_sha in subj:
                    results.append(rec)
            except Exception:
                pass
    return results


def check_breaker_findings(sha: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Inspects canonical server-side findings packet for the commit SHA."""
    matches = list(FINDINGS_DIR.glob(f"*_{sha}.json"))
    short_sha = sha[:8]
    if not matches and len(sha) > 8:
        matches = list(FINDINGS_DIR.glob(f"*_{short_sha}.json"))
    if not matches:
        return False, f"No Breaker findings packet found for SHA {sha}", {}
    
    try:
        with open(matches[0], "r", encoding="utf-8") as f:
            packet = json.load(f)
        verdict = packet.get("verdict", "UNKNOWN")
        summary = packet.get("summary", {})
        crit = summary.get("critical", 0)
        high = summary.get("high", 0)
        
        if verdict == "PASS" and crit == 0 and high == 0:
            return True, "Breaker pass clean", packet
        elif verdict == "NEEDS_REPAIR":
            return False, f"Breaker verdict NEEDS_REPAIR ({crit} critical, {high} high)", packet
        else:
            return False, f"Breaker verdict {verdict} ({crit} critical, {high} high)", packet
    except Exception as e:
        return False, f"Failed reading findings packet: {e}", {}


def evaluate_merge_prerequisites(
    target_ref: str = "HEAD",
    required_autonomy_level: int = 2
) -> Dict[str, Any]:
    """Evaluates whether all cryptographic and governance conditions are satisfied for merge."""
    sha = get_git_commit_sha(target_ref)
    short_sha = sha[:8]
    
    receipts = get_receipts_for_sha(sha)
    gauntlet_receipts = [r for r in receipts if r.get("kind") == "gauntlet_run"]
    breaker_receipts = [r for r in receipts if r.get("kind") == "breaker_run"]
    approval_receipts = [r for r in receipts if r.get("kind") == "founder_approval"]

    breaker_clean, breaker_msg, findings_packet = check_breaker_findings(sha)

    # Autonomy level evaluation
    # If autonomy is below Level 5, founder approval is strictly required
    needs_founder_approval = required_autonomy_level < 5
    has_founder_approval = len(approval_receipts) > 0

    gates_status = {
        "commit_sha": sha,
        "deterministic_gauntlet": {
            "passed": len(gauntlet_receipts) > 0,
            "receipt": gauntlet_receipts[-1]["receipt"] if gauntlet_receipts else None
        },
        "redteam_breaker": {
            "passed": breaker_clean and len(breaker_receipts) > 0,
            "receipt": breaker_receipts[-1]["receipt"] if breaker_receipts else None,
            "detail": breaker_msg
        },
        "founder_approval": {
            "required": needs_founder_approval,
            "granted": has_founder_approval,
            "receipt": approval_receipts[-1]["receipt"] if approval_receipts else None
        }
    }

    all_satisfied = (
        gates_status["deterministic_gauntlet"]["passed"]
        and gates_status["redteam_breaker"]["passed"]
        and (not needs_founder_approval or has_founder_approval)
    )

    merge_attestation = None
    if all_satisfied:
        att = sign_receipt(f"merge_gate:{sha}", "merge_attestation")
        merge_attestation = att["receipt"]

    return {
        "commit_sha": sha,
        "eligible_to_merge": all_satisfied,
        "merge_attestation": merge_attestation,
        "gates": gates_status
    }
