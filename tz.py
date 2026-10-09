#!/usr/bin/env python3
"""TeamZero Unified CLI (`tz`).

The single operational interface for the solo developer CEO.
Unifies quality gates, red teaming, asks inbox triage, and merge authority closure.

Usage:
  python tz.py status             # Org vitals, payroll, and open asks
  python tz.py inbox              # Interactive coffee-time Asks triage
  python tz.py gauntlet           # Run deterministic test gauntlet & sign receipt
  python tz.py breaker [--demo]   # Run L1 Breaker red team pass
  python tz.py check-merge        # Evaluate merge gate prerequisites for HEAD
  python tz.py audit              # Run anti-slop codebase audit
  python tz.py wargame            # Execute L2/L3 war game scenarios
"""

from __future__ import annotations
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from teamzero.config import (
    ORG_DIR,
    TRUST_LEDGER,
    PAYROLL_LEDGER,
    RECEIPTS_LEDGER,
    ASKS_DIR,
    DECISIONS_DIR
)
from teamzero.governance import sign_receipt, load_constitution
from teamzero.merge_gate import evaluate_merge_prerequisites
from teamzero.inbox_triage import interactive_triage, print_summary

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def cmd_status():
    """Prints TeamZero organizational health, trust table, and token burn."""
    print("=" * 65)
    print(" TeamZero Organization Status")
    print("=" * 65)
    
    # 1. Constitution
    const = load_constitution()
    gov = const.get("governance", {})
    auto_lvl = gov.get("token_budget_governor", {}).get("default_autonomy_level", 2)
    print(f" Quality Constitution:  v{const.get('organization',{}).get('version','1.0.0')} (ACTIVE)")
    print(f" Default Autonomy:      Level {auto_lvl} (Founder Approval Required for Merges)")

    # 2. Inbox Counts
    open_asks = len(list(ASKS_DIR.glob("*.json"))) if ASKS_DIR.exists() else 0
    open_decisions = len(list(DECISIONS_DIR.glob("*.json"))) if DECISIONS_DIR.exists() else 0
    print(f" Pending Asks:          {open_asks} open items")
    print(f" Proposed ADRs:         {open_decisions} queued")

    # 3. Payroll / Tokens
    total_tokens = 0
    total_cost = 0.0
    if PAYROLL_LEDGER.exists():
        with open(PAYROLL_LEDGER, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        rec = json.loads(line)
                        total_tokens += rec.get("total_tokens", 0)
                        total_cost += rec.get("cost_usd", 0.0)
                    except Exception:
                        pass
    print(f" Total Payroll Burn:    {total_tokens:,} tokens (${total_cost:.4f} USD)")

    # 4. Agent Trust Scores
    print("\n Agent Trust Ledger:")
    print(f" {'AGENT / CLIENT ID':<30} | {'TRUST':<6} | {'AUTONOMY':<8}")
    print(" " + "-" * 50)
    seen_agents = set()
    if TRUST_LEDGER.exists():
        with open(TRUST_LEDGER, "r", encoding="utf-8") as f:
            for line in reversed(list(f)):
                if line.strip():
                    try:
                        rec = json.loads(line)
                        aid = rec.get("agent_id")
                        if aid and aid not in seen_agents:
                            seen_agents.add(aid)
                            score = rec.get("trust_score", 100)
                            auto = rec.get("autonomy_level", 2)
                            print(f" {aid:<30} | {score:<6} | Level {auto}")
                    except Exception:
                        pass
    print("=" * 65)


def cmd_gauntlet():
    """Runs the deterministic gauntlet locally and emits a signed receipt."""
    print("[*] Dispatching Deterministic Quality Gauntlet...")
    res = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/"], text=True)
    if res.returncode == 0:
        sha_proc = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
        sha = sha_proc.stdout.strip() if sha_proc.returncode == 0 else "00000000"
        receipt = sign_receipt(f"gauntlet_run:{sha}", "gauntlet_run")
        print(f"\n[PASS] Gauntlet verified.")
        print(f"Cryptographic Receipt: {receipt['receipt']}")
    else:
        print(f"\n[FAIL] Gauntlet failed. Code must be repaired.")
        sys.exit(1)


def cmd_breaker(demo: bool = False, candidate: str = None):
    """Runs the L1 Red Team Breaker Pass."""
    cmd = [sys.executable, "l1_pass.py"]
    if demo:
        cmd.extend(["--demo", "--offline"])
    elif candidate:
        cmd.extend(["--candidate", candidate])
    else:
        cmd.extend(["--live", "--offline"])
    subprocess.run(cmd)


def cmd_check_merge(ref: str = "HEAD"):
    """Evaluates whether target commit satisfies all prerequisites for merge."""
    print(f"[*] Evaluating Merge Gate Authority for {ref}...")
    res = evaluate_merge_prerequisites(target_ref=ref)
    sha = res["commit_sha"]
    gates = res["gates"]

    print("\n" + "=" * 65)
    print(f" Merge Gate Prerequisites Check: SHA {sha[:8]}")
    print("-" * 65)

    g_pass = gates["deterministic_gauntlet"]["passed"]
    g_rec = gates["deterministic_gauntlet"]["receipt"]
    print(f" [1] Deterministic Gauntlet:   {'[PASS]' if g_pass else '[MISSING]'} ({g_rec or 'No receipt'})")

    b_pass = gates["redteam_breaker"]["passed"]
    b_rec = gates["redteam_breaker"]["receipt"]
    b_detail = gates["redteam_breaker"]["detail"]
    print(f" [2] Red Team Breaker:         {'[PASS]' if b_pass else '[FAILED]'} ({b_detail})")

    f_req = gates["founder_approval"]["required"]
    f_grant = gates["founder_approval"]["granted"]
    f_rec = gates["founder_approval"]["receipt"]
    if f_req:
        print(f" [3] Founder Approval Signoff: {'[SIGNED]' if f_grant else '[PENDING]'} ({f_rec or 'Review via tz inbox'})")
    else:
        print(f" [3] Founder Approval Signoff: (Autonomous - Not required at Level 5)")

    print("-" * 65)
    if res["eligible_to_merge"]:
        print(f" [OK] ELIGIBLE TO MERGE")
        print(f" Merge Attestation Receipt: {res['merge_attestation']}")
    else:
        print(f" [BLOCKED] MERGE BLOCKED: Cryptographic prerequisites unsatisfied.")
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(description="TeamZero CLI (`tz`)")
    subparsers = parser.add_subparsers(dest="subcommand", help="Command to run")

    subparsers.add_parser("status", help="Show organization status, vitals, and trust scores")
    
    inbox_p = subparsers.add_parser("inbox", help="Open Asks Inbox triage terminal")
    inbox_p.add_argument("--summary", action="store_true", help="Print summary without prompt")

    subparsers.add_parser("gauntlet", help="Run deterministic test gauntlet")
    
    breaker_p = subparsers.add_parser("breaker", help="Run L1 Red Team Breaker pass")
    breaker_p.add_argument("--demo", action="store_true", help="Run offline demo candidate")
    breaker_p.add_argument("--candidate", type=str, help="Candidate manifest file")

    merge_p = subparsers.add_parser("check-merge", help="Check merge gate prerequisites")
    merge_p.add_argument("--ref", type=str, default="HEAD", help="Git reference to evaluate")

    subparsers.add_parser("audit", help="Run anti-slop codebase audit")
    subparsers.add_parser("wargame", help="Run L2/L3 war game scenarios")

    spec_p = subparsers.add_parser("spec", help="Compile decision-table specs to pytest & run mutation audit")
    spec_p.add_argument("--file", type=str, help="Specific spec JSON file")

    args = parser.parse_args()

    if args.subcommand == "status":
        cmd_status()
    elif args.subcommand == "inbox":
        if args.summary:
            print_summary()
        else:
            interactive_triage()
    elif args.subcommand == "gauntlet":
        cmd_gauntlet()
    elif args.subcommand == "breaker":
        cmd_breaker(demo=args.demo, candidate=args.candidate)
    elif args.subcommand == "check-merge":
        cmd_check_merge(ref=args.ref)
    elif args.subcommand == "audit":
        subprocess.run([sys.executable, "slop_audit.py"])
    elif args.subcommand == "wargame":
        subprocess.run([sys.executable, "campaign_runner.py", "--all"])
    elif args.subcommand == "spec":
        from teamzero.spec_compiler import compile_decision_table_to_pytest, run_spec_mutation_audit
        from teamzero.config import SPECS_DIR
        target_spec = Path(args.file) if args.file else (SPECS_DIR / "refund_spec.json")
        out_test = Path("tests") / "test_refund_generated.py"
        c = compile_decision_table_to_pytest(target_spec, out_test)
        print(f"[OK] Compiled {c} decision table rules to {out_test}")
        audit = run_spec_mutation_audit(target_spec)
        print(f"[OK] Spec Mutation Audit: {len(audit)} rules verified.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
