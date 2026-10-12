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

    # 4. Evidence Graph Vitals 
    from teamzero.evidence import EvidenceGraph
    ev_graph = EvidenceGraph()
    all_ev = ev_graph.list_nodes()
    open_ev = [n for n in all_ev if n.status == "OPEN"]
    crit_high_ev = [n for n in open_ev if n.severity in ("CRITICAL", "HIGH")]
    print(f" Evidence Graph:        {len(all_ev)} total nodes ({len(open_ev)} open, {len(crit_high_ev)} blocking)")

    # 5. Agent Trust Scores
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


def cmd_budget():
    """Prints the Budget Awareness Panel (Improvement #7)."""
    const = load_constitution()
    gov = const.get("governance", {})
    cap = gov.get("token_budget_governor", {}).get("max_tokens_per_task", 35000)

    total_tokens = 0
    total_cost = 0.0
    by_agent: dict[str, int] = {}
    by_task: dict[str, int] = {}

    if PAYROLL_LEDGER.exists():
        with open(PAYROLL_LEDGER, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        rec = json.loads(line)
                        tok = rec.get("total_tokens", 0)
                        cost = rec.get("cost_usd", 0.0)
                        aid = rec.get("agent_id", "unknown")
                        tid = rec.get("task_id", "unknown")
                        total_tokens += tok
                        total_cost += cost
                        by_agent[aid] = by_agent.get(aid, 0) + tok
                        by_task[tid] = by_task.get(tid, 0) + tok
                    except Exception:
                        pass

    from teamzero.evidence import EvidenceGraph
    ev_graph = EvidenceGraph()
    ev_nodes = ev_graph.list_nodes()
    # Estimated savings: resolved nodes prevent breaker re-probing (~1,500 tokens per resolved node)
    resolved_count = len([n for n in ev_nodes if n.status == "RESOLVED"])
    est_savings = resolved_count * 1500

    pct = min(100.0, (total_tokens / cap) * 100) if cap > 0 else 0.0
    costliest_agent = max(by_agent.items(), key=lambda x: x[1]) if by_agent else ("None", 0)
    cheapest_task = min(by_task.items(), key=lambda x: x[1]) if by_task else ("None", 0)

    print("+" + "=" * 60 + "+")
    print(f"|{'TeamZero Budget Awareness Panel':^60}|")
    print("+" + "=" * 60 + "+")
    print(f"| Token Budget Cap:          {cap:>10,} tokens                  |")
    print(f"| Tokens Consumed:           {total_tokens:>10,} tokens ({pct:5.1f}%)        |")
    print(f"| Total Payroll Cost:        ${total_cost:>9.4f} USD                    |")
    print(f"| Top Token Consumer:        {costliest_agent[0][:20]:<20} ({costliest_agent[1]:,} tok) |")
    print(f"| Leanest Task:              {cheapest_task[0][:20]:<20} ({cheapest_task[1]:,} tok) |")
    print("+" + "-" * 60 + "+")
    print(f"| Evidence Graph Savings:    ~{est_savings:>9,} tokens ({resolved_count} bugs fixed) |")
    print("+" + "=" * 60 + "+")


def cmd_evidence():
    """Prints all nodes in the Typed Evidence Graph (Improvement #1)."""
    from teamzero.evidence import EvidenceGraph
    ev_graph = EvidenceGraph()
    nodes = ev_graph.list_nodes()

    print("=" * 70)
    print(" TeamZero Typed Evidence Graph")
    print("=" * 70)
    if not nodes:
        print(" [i] Evidence graph is empty. Run `tz breaker` to populate findings.")
        print("=" * 70)
        return

    for n in nodes:
        status_sym = "[x]" if n.status == "OPEN" else "[v]"
        print(f" {status_sym} [{n.severity:<8}] {n.node_id} ({n.type})")
        print(f"     Task:       {n.task_id} (Gen {n.generation})")
        print(f"     Claim:      {n.claim}")
        print(f"     Evidence:   {n.evidence[:80]}")
        if n.resolved_by_commit:
            print(f"     Resolved:   commit {n.resolved_by_commit[:8]}")
        print(" " + "-" * 66)
    print("=" * 70)


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

    e_gate = gates.get("evidence_graph", {})
    e_pass = e_gate.get("passed", True)
    e_detail = e_gate.get("detail", "Clean")
    print(f" [3] Evidence Graph Safety:    {'[PASS]' if e_pass else '[BLOCKED]'} ({e_detail})")

    f_req = gates["founder_approval"]["required"]
    f_grant = gates["founder_approval"]["granted"]
    f_rec = gates["founder_approval"]["receipt"]
    if f_req:
        print(f" [4] Founder Approval Signoff: {'[SIGNED]' if f_grant else '[PENDING]'} ({f_rec or 'Review via tz inbox'})")
    else:
        print(f" [4] Founder Approval Signoff: (Autonomous - Not required at Level 5)")

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
    inbox_p.add_argument("--approve", type=str, help="Approve and sign a specific ask ID")

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

    subparsers.add_parser("budget", help="Display real-time Budget Awareness Panel")
    subparsers.add_parser("evidence", help="List all nodes in Typed Evidence Graph")

    race_p = subparsers.add_parser("race", help="Race parallel peer hypotheses against a spec (Improvement #3)")
    race_p.add_argument("--spec", type=str, default=".teamzero/memory/specs/refund_spec.json", help="Spec file to race against")
    race_p.add_argument("--peers", type=int, default=3, help="Number of peer hypotheses to race (default: 3)")

    synth_p = subparsers.add_parser("synthesize", help="Synthesize task learnings into an ADR & Living Map (Improvement #6)")
    synth_p.add_argument("--task", type=str, required=True, help="Task ID to synthesize (e.g. TASK-REFUND-CLEAN-001)")

    canary_p = subparsers.add_parser("canary", help="View canary security event lineage (Improvement #8)")
    canary_p.add_argument("--list", action="store_true", help="List all past canary breach events")

    ratchet_p = subparsers.add_parser("ratchet", help="Audit and self-heal ratchet checks (Improvement #10)")
    ratchet_p.add_argument("--health", action="store_true", help="Display ratchet health & proposed promotions")

    args = parser.parse_args()

    if args.subcommand == "status":
        cmd_status()
    elif args.subcommand == "inbox":
        if args.summary:
            print_summary()
        elif args.approve:
            from teamzero.inbox_triage import resolve_ask
            from teamzero.config import ASKS_DIR
            target = ASKS_DIR / f"{args.approve}.json"
            if not target.exists():
                target = ASKS_DIR / args.approve
            if target.exists():
                resolve_ask(target, "APPROVE")
            else:
                print(f"Ask '{args.approve}' not found in {ASKS_DIR}")
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
    elif args.subcommand == "budget":
        cmd_budget()
    elif args.subcommand == "evidence":
        cmd_evidence()
    elif args.subcommand == "race":
        from teamzero.racing import race_peer_hypotheses
        spec_path = Path(args.spec)
        res = race_peer_hypotheses(spec_path, num_peers=args.peers)
        print("\n" + "=" * 65)
        print(f" Hypothesis Racing Results (Spec: {res['spec_id']})")
        print("=" * 65)
        for idx, p in enumerate(res["leaderboard"], 1):
            star = "[WINNER]" if idx == 1 else "        "
            print(f" #{idx} {star} {p['name']:<25} | Score: {p['score']:>5.1f}/100")
        print("=" * 65)
    elif args.subcommand == "synthesize":
        from teamzero.synthesize import synthesize_task_learnings
        res = synthesize_task_learnings(args.task)
        print(f"[OK] Generated Synthesis ADR: {res['adr_file']}")
        if res["map_updated"]:
            print(f"[OK] Updated Living Map Card for {args.task}")
    elif args.subcommand == "canary":
        from teamzero.canary_lineage import list_canary_events
        events = list_canary_events()
        print("=" * 65)
        print(f" Canary Security Lineage Events ({len(events)} logged)")
        print("=" * 65)
        if not events:
            print(" [i] Clean: No canary breaches recorded in organizational history.")
        else:
            for ev in events:
                print(f" [!] {ev['event_id']} ({ev['timestamp']})")
                print(f"     Canary:    {ev['canary_id']}")
                print(f"     Task:      {ev['task_id']}")
                print(f"     File:      {ev['leaked_file']}")
        print("=" * 65)
    elif args.subcommand == "ratchet":
        from teamzero.ratchet import audit_ratchet_health
        health = audit_ratchet_health()
        print("=" * 65)
        print(" TeamZero Ratchet Health & Self-Healing Report")
        print("=" * 65)
        print(f" Total Registered Checks: {health['total_checks']}")
        print(f" Active Checks:           {health['active_count']}")
        print(f" Stale Checks:            {health['stale_count']}")
        if health["proposed_promotions"]:
            print(f"\n Auto-Proposed Promotions from Evidence Graph ({len(health['proposed_promotions'])}):")
            for prop in health["proposed_promotions"]:
                print(f"  + [{prop['id']}] {prop['description']}")
        print("=" * 65)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
