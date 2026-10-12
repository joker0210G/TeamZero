#!/usr/bin/env python3
"""TeamZero L2/L3 War Game Campaign Runner.

Executes adversarial scenarios against the organization's defenses and verifies
whether canary tokens leak into tool calls, diffs, or outbound responses.
Implements the ratchet mechanism: every verified escape becomes an automated check.
"""

from __future__ import annotations
import argparse
import glob
import json
import os
import re
import sys
import yaml
from pathlib import Path
from typing import Any, Dict, List

from teamzero.config import CAMPAIGNS_DIR, ORG_DIR
from teamzero.governance import scan_for_poison, sign_receipt, update_trust_score


def run_campaign(campaign_file: Path) -> Dict[str, Any]:
    print(f"\n[+] Executing Campaign: {campaign_file.name}")
    data = yaml.safe_load(campaign_file.read_text(encoding="utf-8"))
    
    cid = data.get("id", "UNKNOWN")
    level = data.get("level", 2)
    canary = data.get("canary", "")
    payload = data.get("payload", "")
    target = data.get("target_artifact", "")
    
    print(f"    Level: {level} | Target: {target} | Canary: {canary}")
    
    # 1. Test Static Defense: Poison Pattern Scanner
    hits = scan_for_poison(payload)
    print(f"    [Step 1] L2 Poison Sentinel Scan: {len(hits)} pattern hits")
    for hit in hits:
        print(f"      - {hit}")

    # 2. Simulate Ingestion & Canary Leak Check
    # Verify that outbound envelopes and validators prevent canary propagation
    leaked = False
    leak_locations = []
    
    # Check if canary is caught before entering memory
    if hits:
        print("    [Step 2] Attack BLOCKED at the door by L2 Sentinel.")
    else:
        # If not caught by patterns, simulate downstream check
        print("    [Step 2] Attack bypassed initial filters! Checking canary leaks...")
        # Check logs and inbox
        for log_file in ORG_DIR.rglob("*.json*"):
            if log_file.is_file():
                content = log_file.read_text(encoding="utf-8", errors="ignore")
                if canary in content:
                    leaked = True
                    leak_locations.append(str(log_file))

    if leaked:
        from teamzero.canary_lineage import log_canary_event
        for loc in leak_locations:
            log_canary_event(
                canary_id=canary,
                campaign_id=cid,
                leaked_file=loc,
                target_task_id=f"TASK-CAMPAIGN-{cid}"
            )

    status = "DEFENSE_HELD" if (hits and not leaked) else "ESCAPE_DETECTED"
    print(f"    Campaign Verdict: {status}")
    
    receipt = sign_receipt(f"campaign:{cid}", "war_game")
    
    return {
        "campaign_id": cid,
        "level": level,
        "verdict": status,
        "canary_leaked": leaked,
        "leak_locations": leak_locations,
        "sentinel_hits": hits,
        "receipt": receipt["receipt"]
    }


def main():
    parser = argparse.ArgumentParser(description="TeamZero Campaign Runner")
    parser.add_argument("--all", action="store_true", help="Run all campaigns in .teamzero/redteam/campaigns/")
    parser.add_argument("--file", type=str, help="Run specific campaign file")
    args = parser.parse_args()

    files = []
    if args.file:
        files = [Path(args.file)]
    elif args.all or len(sys.argv) == 1:
        files = list(CAMPAIGNS_DIR.glob("*.yaml"))

    if not files:
        print("No campaigns found in", CAMPAIGNS_DIR)
        return

    print("=" * 65)
    print(" TeamZero L2/L3 War Game Campaign Harness")
    print("=" * 65)

    results = []
    for f in files:
        res = run_campaign(f)
        results.append(res)

    print("\n" + "=" * 65)
    print(f" Summary: {len(results)} campaigns evaluated.")
    for r in results:
        print(f"  * {r['campaign_id']}: {r['verdict']} (Receipt: {r['receipt']})")
    print("=" * 65)


if __name__ == "__main__":
    main()
