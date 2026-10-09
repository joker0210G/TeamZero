"""Interactive Founder Asks Inbox & Decision Triage Terminal.

The bridge between founder judgment and automated execution.
Batch 5 decisions over coffee:
- Review escalated questions, spec diffs, and candidate merge packets.
- Issue cryptographic founder approval receipts (TZ-founder_approval:<sha>).
- Move resolved items to .teamzero/inbox/resolved/.
"""

from __future__ import annotations
import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from teamzero.config import (
    ORG_DIR,
    INBOX_DIR,
    ASKS_DIR,
    DECISIONS_DIR,
    RECEIPTS_LEDGER
)
from teamzero.governance import sign_receipt, update_trust_score

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

RESOLVED_DIR = INBOX_DIR / "resolved"


def get_pending_asks() -> List[Path]:
    """Returns sorted list of pending ask files."""
    if not ASKS_DIR.exists():
        return []
    return sorted(list(ASKS_DIR.glob("*.json")), key=lambda p: p.stat().st_mtime)


def get_pending_decisions() -> List[Path]:
    """Returns sorted list of pending ADR proposals."""
    if not DECISIONS_DIR.exists():
        return []
    return sorted(list(DECISIONS_DIR.glob("*.json")), key=lambda p: p.stat().st_mtime)


def print_ask_card(ask_path: Path, index: int, total: int):
    """Renders a clean terminal card for an escalated ask."""
    try:
        data = json.loads(ask_path.read_text(encoding="utf-8"))
    except Exception:
        return

    sev = data.get("severity", "medium").upper()
    sev_badge = f"[{sev}]"
    agent = data.get("from_agent") or data.get("author_agent", "unknown")
    q = data.get("question") or data.get("reason", "No description provided.")
    sha = data.get("commit_sha", "")
    task_id = data.get("task_id", "")

    print("\n" + "=" * 70)
    print(f" ASK [{index}/{total}] {sev_badge} ID: {ask_path.stem}")
    print(f" Source: {agent} | Task: {task_id} | SHA: {sha[:8] if sha else 'N/A'}")
    print("-" * 70)
    print(f" Question / Context:\n   {q}\n")

    findings = data.get("findings", [])
    if findings:
        print(" Critical Breaker Findings:")
        for f in findings[:3]:
            print(f"   * [{f.get('severity','').upper()}] {f.get('title')}")
            if f.get("repro"):
                print(f"     Repro: {f.get('repro')}")

    options = data.get("options", [])
    if options:
        print("\n Options:")
        for i, opt in enumerate(options, 1):
            print(f"   [{i}] {opt}")
    print("=" * 70)


def resolve_ask(
    ask_path: Path,
    decision: str,
    choice_text: str = "",
    commit_sha: str = ""
):
    """Resolves an ask, issues approval receipt if approved, and archives to resolved/."""
    try:
        data = json.loads(ask_path.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    sha = commit_sha or data.get("commit_sha", "")
    agent = data.get("from_agent") or data.get("author_agent", "unknown")

    receipt = None
    if decision == "APPROVE" and sha:
        receipt_rec = sign_receipt(f"founder_approval:{sha}", "founder_approval")
        receipt = receipt_rec["receipt"]
        update_trust_score(agent, delta=+3, reason=f"Founder approved candidate {sha[:8]}")
        print(f"\n [OK] Cryptographic Approval Signed: {receipt}")
    elif decision == "REJECT":
        update_trust_score(agent, delta=-2, reason=f"Founder rejected candidate {sha[:8] if sha else 'task'}")
        print("\n [REJECT] Candidate Rejected. Routed back for repair.")

    # Record resolution
    RESOLVED_DIR.mkdir(parents=True, exist_ok=True)
    resolution_record = {
        "original_ask": data,
        "resolved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "founder_decision": decision,
        "selected_option": choice_text,
        "approval_receipt": receipt
    }
    
    dest_path = RESOLVED_DIR / ask_path.name
    with open(dest_path, "w", encoding="utf-8") as f:
        json.dump(resolution_record, f, indent=2)

    try:
        ask_path.unlink()
    except Exception:
        pass


def interactive_triage():
    """Runs the interactive decision loop in terminal."""
    pending = get_pending_asks()
    decisions = get_pending_decisions()

    if not pending and not decisions:
        print("\n [OK] Asks Inbox is completely clear. No decisions pending.")
        return

    print(f"\n [!] TeamZero Asks Inbox: {len(pending)} open asks, {len(decisions)} ADR proposals.")

    for idx, ask_path in enumerate(pending, 1):
        print_ask_card(ask_path, idx, len(pending))
        try:
            data = json.loads(ask_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        options = data.get("options", [])
        sha = data.get("commit_sha", "")

        prompt_str = " Decision: [A]pprove & Sign | [R]eject | [S]kip | [Q]uit"
        if options:
            prompt_str = f" Decision: [1-{len(options)}] Select Option | [A]pprove | [R]eject | [S]kip | [Q]uit"
        
        choice = input(f"\n{prompt_str} > ").strip().upper()

        if choice == "Q":
            print("\n Exiting triage.")
            break
        elif choice == "S":
            print(" Skipped.")
            continue
        elif choice == "A":
            resolve_ask(ask_path, "APPROVE", choice_text="Founder Approved", commit_sha=sha)
        elif choice == "R":
            resolve_ask(ask_path, "REJECT", choice_text="Founder Rejected", commit_sha=sha)
        elif choice.isdigit() and 1 <= int(choice) <= len(options):
            selected = options[int(choice) - 1]
            resolve_ask(ask_path, "CHOSEN_OPTION", choice_text=selected, commit_sha=sha)
            print(f" [OK] Decision saved: '{selected}'")
        else:
            print(" Unrecognized input. Item left pending.")


def print_summary():
    """Prints non-interactive summary of open items."""
    pending = get_pending_asks()
    decisions = get_pending_decisions()
    print("=" * 60)
    print(" TeamZero Inbox Summary")
    print("=" * 60)
    print(f" Open Asks:       {len(pending)}")
    print(f" Open Decisions:  {len(decisions)}")
    for p in pending:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            print(f"  * [{d.get('severity','?').upper()}] {p.name}: {d.get('question', d.get('reason',''))[:60]}...")
        except Exception:
            pass
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TeamZero Asks Inbox Triage")
    parser.add_argument("--summary", action="store_true", help="Print summary without interactive prompt")
    parser.add_argument("--approve", type=str, help="Approve and sign a specific ask ID")
    args = parser.parse_args()

    if args.summary:
        print_summary()
    elif args.approve:
        target = ASKS_DIR / f"{args.approve}.json"
        if not target.exists():
            target = ASKS_DIR / args.approve
        if target.exists():
            resolve_ask(target, "APPROVE")
        else:
            print(f"Ask {args.approve} not found.")
    else:
        interactive_triage()
