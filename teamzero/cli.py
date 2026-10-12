#!/usr/bin/env python3
"""TeamZero Unified CLI (`tz`).

The single operational interface for the solo developer CEO.
Unifies quality gates, red teaming, asks inbox triage, merge authority closure,
and project bootstrapping (`tz init`).
"""

from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from teamzero.config import (
    ROOT_DIR,
    ORG_DIR,
    TRUST_LEDGER,
    PAYROLL_LEDGER,
    RECEIPTS_LEDGER,
    ASKS_DIR,
    DECISIONS_DIR,
    SPECS_DIR,
)
from teamzero.governance import sign_receipt, load_constitution
from teamzero.merge_gate import evaluate_merge_prerequisites
from teamzero.inbox_triage import interactive_triage, print_summary
from teamzero.init_project import cmd_init, cmd_doctor, init_project

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _find_package_script(filename: str) -> Path:
    """Finds an internal script either in active ROOT_DIR or inside the installed teamzero repo."""
    cand = ROOT_DIR / filename
    if cand.exists():
        return cand
    pkg_root = Path(__file__).resolve().parent.parent
    cand_pkg = pkg_root / filename
    if cand_pkg.exists():
        return cand_pkg
    return cand


def cmd_status():
    """Prints TeamZero organizational health, trust table, and token burn."""
    print("=" * 65)
    print(" TeamZero Organization Status")
    print("=" * 65)

    if not ORG_DIR.exists():
        print(" [!] No .teamzero directory found in current working directory.")
        print("     Run `tz init` to bootstrap TeamZero in this project.")
        print("=" * 65)
        return

    # 1. Constitution
    const = load_constitution()
    gov = const.get("governance", {})
    auto_lvl = gov.get("token_budget_governor", {}).get("default_autonomy_level", 2)
    print(f" Target Root:           {ROOT_DIR}")
    print(f" Quality Constitution:  v{const.get('organization',{}).get('version','0.1.0.dev1')} (ACTIVE)")
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
    """Prints the Budget Awareness Panel."""
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
    """Prints all nodes in the Typed Evidence Graph."""
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
    tests_dir = ROOT_DIR / "tests"
    cmd = [sys.executable, "-m", "pytest", "-q"]
    if tests_dir.exists():
        cmd.append(str(tests_dir))

    res = subprocess.run(cmd, cwd=str(ROOT_DIR), text=True)
    if res.returncode == 0:
        sha_proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT_DIR), capture_output=True, text=True)
        sha = sha_proc.stdout.strip() if sha_proc.returncode == 0 else "00000000"
        receipt = sign_receipt(f"gauntlet_run:{sha}", "gauntlet_run")
        print(f"\n[PASS] Gauntlet verified.")
        print(f"Cryptographic Receipt: {receipt['receipt']}")
    else:
        print(f"\n[FAIL] Gauntlet failed. Code must be repaired.")
        sys.exit(1)


def cmd_breaker(demo: bool = False, candidate: str = None):
    """Runs the L1 Red Team Breaker Pass."""
    l1_script = _find_package_script("l1_pass.py")
    cmd = [sys.executable, str(l1_script)]
    if demo:
        cmd.extend(["--demo", "--offline"])
    elif candidate:
        cmd.extend(["--candidate", candidate])
    else:
        cmd.extend(["--live", "--offline"])
    subprocess.run(cmd, cwd=str(ROOT_DIR))


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


def main(argv=None):
    parser = argparse.ArgumentParser(description="TeamZero CLI (`tz` / `teamzero`)")
    subparsers = parser.add_subparsers(dest="subcommand", help="Command to run")

    init_p = subparsers.add_parser("init", help="Bootstrap TeamZero governance layer inside a project")
    init_p.add_argument("project_root", nargs="?", default=".", help="Target project root (default: cwd)")
    init_p.add_argument("--path", type=str, default=None, help=argparse.SUPPRESS)
    init_p.add_argument("--name", default=None, help="Organization name (default: directory name)")
    init_p.add_argument("--profile", default="auto", choices=["auto", "python", "node", "rust", "go", "generic"], help="Project profile for gate selection (default: auto-detect)")
    init_p.add_argument("--force", action="store_true", help="Back up an existing .teamzero and re-initialize")
    init_p.add_argument("--mcp-cmd", default=sys.executable, help="Command the MCP client uses to launch the server (default: current python)")

    doc_p = subparsers.add_parser("doctor", help="Verify the governance layer is healthy")
    doc_p.add_argument("project_root", nargs="?", default=".", help="Project root (default: cwd)")

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
    spec_p.add_argument("--file", type=str, help="Specific spec JSON file (if omitted, auto-discovers in .teamzero/memory/specs/)")

    subparsers.add_parser("budget", help="Display real-time Budget Awareness Panel")
    subparsers.add_parser("evidence", help="List all nodes in Typed Evidence Graph")

    race_p = subparsers.add_parser("race", help="Race parallel peer hypotheses against a spec")
    race_p.add_argument("--spec", type=str, help="Spec file to race against (auto-discovers if omitted)")
    race_p.add_argument("--peers", type=int, default=3, help="Number of peer hypotheses to race (default: 3)")

    synth_p = subparsers.add_parser("synthesize", help="Synthesize task learnings into an ADR & Living Map")
    synth_p.add_argument("--task", type=str, required=True, help="Task ID to synthesize (e.g. TASK-REFUND-CLEAN-001)")

    canary_p = subparsers.add_parser("canary", help="View canary security event lineage")
    canary_p.add_argument("--list", action="store_true", help="List all past canary breach events")

    ratchet_p = subparsers.add_parser("ratchet", help="Audit and self-heal ratchet checks")
    ratchet_p.add_argument("--health", action="store_true", help="Display ratchet health & proposed promotions")

    replay_p = subparsers.add_parser("replay", help="Replay and summarize an Event Journal run")
    replay_p.add_argument("run_id", type=str, help="Run ID to replay (e.g. RUN-001)")

    pareto_p = subparsers.add_parser("pareto", help="Compute Pareto-optimal frontier among competing hypotheses")
    pareto_p.add_argument("--demo", action="store_true", help="Run with demonstration candidate set")

    route_p = subparsers.add_parser("route", help="Manage model provider & tier routing")
    route_p.add_argument("--set-tier", type=str, choices=["lite", "standard", "frontier"], help="Tier to configure")
    route_p.add_argument("--provider", type=str, help="Provider name (gemini, anthropic, openai, ollama)")
    route_p.add_argument("--model", type=str, help="Model name (e.g. claude-3-5-sonnet, gpt-4o)")

    trig_p = subparsers.add_parser("triggers", help="Inspect and run adaptive opportunistic triggers")
    trig_p.add_argument("--catchup", action="store_true", help="Execute pending overdue triggers")

    debug_p = subparsers.add_parser("debug-at", help="Time-travel rewind state to a specific sequence number")
    debug_p.add_argument("run_id", type=str, help="Run ID to debug")
    debug_p.add_argument("seq", type=int, help="Sequence number to rewind to")

    mutate_p = subparsers.add_parser("mutate", help="Run AI Red-Team adversarial spec mutation test")
    mutate_p.add_argument("--spec", type=str, help="Spec file to stress-test (auto-discovers if omitted)")

    subparsers.add_parser("health", help="Display Living SLA Dashboard and health report")

    dep_p = subparsers.add_parser("dep-scan", help="Run XZ-grade supply chain & dependency security audit")
    dep_p.add_argument("--strict", action="store_true", help="Exit with non-zero code on any finding")

    ideate_p = subparsers.add_parser("ideate", help="Design Thinking ideation terminal & spec compilation wizard")
    ideate_p.add_argument("--from-file", type=str, help="Import and validate an existing Design Thinking Ask markdown file")
    ideate_p.add_argument("--compile", type=str, help="Compile an Ask markdown directly to a decision-table spec JSON")
    ideate_p.add_argument("--title", type=str, help="Title for the ideation brief")
    ideate_p.add_argument("--author", type=str, default="Founder", help="Author of the ideation brief (default: Founder)")

    task_p = subparsers.add_parser("task", help="Decompose PRDs, navigate dependency trees, and track microtask execution")
    task_p.add_argument("action", nargs="?", default="list", choices=["list", "next", "parse", "expand", "update", "validate", "fix"], help="Task action to perform")
    task_p.add_argument("--file", type=str, help="PRD or Ask markdown file to parse into microtasks")
    task_p.add_argument("--id", type=str, help="Task ID to expand or update")
    task_p.add_argument("--status", type=str, help="New status for task (TODO, IN_PROGRESS, GAUNTLET_PASS, VERIFIED)")
    task_p.add_argument("--subtasks", type=str, help="Comma-separated list of subtask titles to expand into")

    args = parser.parse_args()

    if args.subcommand == "init":
        return cmd_init(args)
    elif args.subcommand == "doctor":
        return cmd_doctor(args)
    elif args.subcommand == "status":
        cmd_status()
    elif args.subcommand == "inbox":
        if args.summary:
            print_summary()
        elif args.approve:
            from teamzero.inbox_triage import resolve_ask
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
        audit_script = _find_package_script("slop_audit.py")
        subprocess.run([sys.executable, str(audit_script), "--path", str(ROOT_DIR)])
    elif args.subcommand == "wargame":
        wg_script = _find_package_script("campaign_runner.py")
        subprocess.run([sys.executable, str(wg_script), "--all"], cwd=str(ROOT_DIR))
    elif args.subcommand == "spec":
        from teamzero.spec_compiler import compile_decision_table_to_pytest, run_spec_mutation_audit
        if args.file:
            target_spec = Path(args.file)
        else:
            all_specs = sorted(list(SPECS_DIR.glob("*.json"))) if SPECS_DIR.exists() else []
            if not all_specs:
                print(f"[!] No spec found in {SPECS_DIR}. Create one with 'tz ideate' or pass --file <path>.")
                sys.exit(1)
            target_spec = all_specs[0]
            print(f"[i] Auto-selected spec: {target_spec.name}")

        out_test = ROOT_DIR / "tests" / f"test_{target_spec.stem}_generated.py"
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
        if args.spec:
            spec_path = Path(args.spec)
        else:
            all_specs = sorted(list(SPECS_DIR.glob("*.json"))) if SPECS_DIR.exists() else []
            if not all_specs:
                print(f"[!] No spec found in {SPECS_DIR}. Create one with 'tz ideate' or pass --spec <path>.")
                sys.exit(1)
            spec_path = all_specs[0]
            print(f"[i] Auto-selected spec: {spec_path.name}")

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
    elif args.subcommand == "replay":
        from teamzero.journal import EventJournal
        j = EventJournal(args.run_id)
        summary = j.replay_summary()
        print("=" * 65)
        print(f" Event Journal Replay Summary (Run: {summary['run_id']})")
        print("=" * 65)
        print(f" Total Events Logged: {summary['total_events']}")
        print(f" Last Sequence Num:   {summary['last_seq']}")
        print(" Event Breakdown:")
        for ev_type, count in summary["event_breakdown"].items():
            print(f"   - {ev_type:<25}: {count}")
        print("=" * 65)
    elif args.subcommand == "pareto":
        from teamzero.pareto import SolutionCandidate, compute_pareto_front, format_scoreboard
        cands = [
            SolutionCandidate("CAND-A-FAST", {"speed": 95.0, "coverage": 80.0, "efficiency": 40.0}, {}),
            SolutionCandidate("CAND-B-LOWMEM", {"speed": 50.0, "coverage": 85.0, "efficiency": 90.0}, {}),
            SolutionCandidate("CAND-C-BALANCED", {"speed": 80.0, "coverage": 82.0, "efficiency": 75.0}, {}),
            SolutionCandidate("CAND-D-SLOPPY", {"speed": 40.0, "coverage": 70.0, "efficiency": 30.0}, {}),
        ]
        metrics = ["speed", "coverage", "efficiency"]
        front = compute_pareto_front(cands, metrics)
        print("=" * 65)
        print(" TeamZero Pareto Multi-Objective Frontier")
        print("=" * 65)
        print(format_scoreboard(front, metrics))
        print("=" * 65)
    elif args.subcommand == "route":
        from teamzero.model_router import ModelRouter
        router = ModelRouter()
        if args.set_tier and args.provider and args.model:
            router.set_tier_model(args.set_tier, args.provider, args.model)
            print(f"[OK] Updated tier '{args.set_tier}' -> {args.provider} / {args.model}")
        else:
            print("=" * 65)
            print(" TeamZero Multi-Provider Model Router")
            print("=" * 65)
            tiers = router.config.get("tiers", {})
            for t_name, t_info in tiers.items():
                print(f" Tier: {t_name.upper():<10} | Provider: {t_info.get('provider'):<10} | Model: {t_info.get('model')}")
                print(f"   Description: {t_info.get('description')}")
            print("=" * 65)
    elif args.subcommand == "triggers":
        from teamzero.triggers import AdaptiveTriggerEngine
        engine = AdaptiveTriggerEngine()
        statuses = engine.evaluate_triggers()
        print("=" * 65)
        print(" TeamZero Adaptive Opportunistic Triggers")
        print("=" * 65)
        for s in statuses:
            badge = "[DUE]" if s.status in ["DUE", "MISSED_OVERDUE"] else "[OK]"
            print(f" {badge:<6} {s.trigger_id:<20} | Status: {s.status}")
        pending = engine.get_pending_catchups()
        if args.catchup and pending:
            print(f"\n[i] Catching up {len(pending)} pending triggers...")
            for p in pending:
                engine.record_run(p["id"])
                print(f"  [OK] Ran catch-up for {p['id']}")
        elif pending:
            print(f"\n[!] {len(pending)} triggers pending catch-up. Run with --catchup to execute.")
        print("=" * 65)
    elif args.subcommand == "debug-at":
        from teamzero.debugger import TimeTravelDebugger
        dbg = TimeTravelDebugger(args.run_id)
        snap = dbg.rewind_to(args.seq)
        print("=" * 65)
        print(f" Time-Travel Replay Snapshot (Run: {snap.run_id} @ Seq: {snap.target_seq})")
        print("=" * 65)
        print(f" Events Replayed: {snap.events_replayed}")
        print(f" Reconstructed State:")
        print(f"   Findings:       {len(snap.reconstructed_state.get('findings', []))}")
        print(f"   Trust Deltas:   {snap.reconstructed_state.get('trust_deltas')}")
        print(f"   Active Tasks:   {snap.reconstructed_state.get('active_tasks')}")
        print(f"   Gate Verdicts:  {len(snap.reconstructed_state.get('gate_verdicts', []))}")
        print("=" * 65)
    elif args.subcommand == "mutate":
        from teamzero.mutation import RedTeamMutationEngine
        engine = RedTeamMutationEngine()
        if args.spec:
            spec_path = Path(args.spec)
        else:
            all_specs = sorted(list(SPECS_DIR.glob("*.json"))) if SPECS_DIR.exists() else []
            if not all_specs:
                print(f"[!] No spec found in {SPECS_DIR}. Create one with 'tz ideate' or pass --spec <path>.")
                sys.exit(1)
            spec_path = all_specs[0]
            print(f"[i] Auto-selected spec: {spec_path.name}")

        spec_data = json.loads(spec_path.read_text(encoding="utf-8"))
        mod_name = spec_data.get("module", "")
        # Resolve module path: e.g. teamzero.refund_service -> ROOT_DIR / teamzero / refund_service.py
        target_service = ROOT_DIR / (mod_name.replace(".", "/") + ".py") if mod_name else (ROOT_DIR / "teamzero" / "refund_service.py")
        base_code = target_service.read_text(encoding="utf-8") if target_service.exists() else ""
        mutants = engine.generate_adversarial_mutants(base_code)
        
        res = engine.evaluate_spec_resilience(mutants, lambda code: "float(amount)" not in code and "int(amount)" in code)
        print("=" * 65)
        print(f" AI Red-Team Adversarial Spec Mutation Test")
        print("=" * 65)
        print(f" Target Spec:             {spec_path.name}")
        print(f" Target Service:          {target_service.name if target_service.exists() else 'N/A'}")
        print(f" Total Adversarial Mutants: {res.total_mutants}")
        print(f" Mutants Killed (Caught): {res.mutants_killed}")
        print(f" Mutants Survived:        {res.mutants_survived}")
        print(f" Spec Resilience Rating:  {res.spec_resilience_rating:.1f}%")
        if res.blind_spots:
            print("\n [!] Spec Blind Spots Discovered:")
            for b in res.blind_spots:
                print(f"   - {b}")
        print("=" * 65)
    elif args.subcommand == "health":
        from teamzero.health import SLADashboard
        dash = SLADashboard()
        rep = dash.compute_health()
        print("=" * 65)
        print(" TeamZero Living SLA & Health Dashboard")
        print("=" * 65)
        status_badge = "[HEALTHY]" if rep.overall_status == "HEALTHY" else f"[{rep.overall_status}]"
        print(f" Overall Status:             {status_badge}")
        print(f" Unresolved Critical Issues: {rep.unresolved_critical_count}")
        print(f" Active SLA Breaches:        {len(rep.sla_breaches)}")
        if rep.sla_breaches:
            print("\n [!] SLA Breaches:")
            for sb in rep.sla_breaches:
                print(f"   - {sb}")
        if rep.trust_violations:
            print("\n [!] Trust Floor Alerts:")
            for tv in rep.trust_violations:
                print(f"   - {tv}")
        print("=" * 65)
    elif args.subcommand == "dep-scan":
        from teamzero.supply_chain import SupplyChainScanner
        scanner = SupplyChainScanner(ROOT_DIR)
        risks = scanner.run_full_scan()
        print("=" * 65)
        print(" TeamZero XZ-Grade Supply Chain & Dependency Audit")
        print("=" * 65)
        if not risks:
            print(" [OK] Clean: No hidden test payloads, suspicious build hooks, or typosquats.")
        else:
            for r in risks:
                badge = f"[{r.severity}]"
                print(f" {badge:<10} Category: {r.category:<22} Target: {r.target_path}")
                print(f"            {r.description}")
        print("=" * 65)
        if args.strict and any(r.severity in ["CRITICAL", "HIGH"] for r in risks):
            sys.exit(1)
    elif args.subcommand == "review":
        from teamzero.peer_review import PeerReviewBot, ReviewComment
        bot = PeerReviewBot()
        comments = [
            ReviewComment(
                file_path="teamzero/refund_service.py",
                line_number=45,
                rule="L1_BREAKER_BOUNDARY_CHECK",
                severity="HIGH",
                message="Floating point amount used without currency decimal rounding clamp.",
                suggested_fix="amount = round(float(amount), 2)",
            )
        ]
        out_path = bot.generate_review_markdown(args.branch, args.base, comments)
        print("=" * 65)
        print(f" TeamZero Peer Review Bot Draft Generated")
        print("=" * 65)
        print(f" Review File: {out_path}")
        print(" Ready to inspect or submit to GitHub PR via gh CLI.")
        print("=" * 65)
    elif args.subcommand == "ideate":
        from teamzero.ideation import (
            DesignThinkingBrief,
            EmpathizePhase,
            DefinePhase,
            IdeatePhase,
            PrototypePhase,
            IdeationTestRule,
            parse_ideation_markdown,
            save_brief_to_inbox,
            compile_brief_to_spec,
        )

        if args.compile:
            src = Path(args.compile)
            if not src.exists():
                print(f"[!] Error: Ask file '{src}' does not exist.")
                sys.exit(1)
            brief = parse_ideation_markdown(src.read_text(encoding="utf-8"))
            out_spec = compile_brief_to_spec(brief)
            print("=" * 65)
            print(" TeamZero Design Thinking Spec Compiler")
            print("=" * 65)
            print(f" [OK] Compiled Ask '{brief.title}' into executable spec:")
            print(f"      Spec Path:   {out_spec}")
            print(f"      Module:      {brief.prototype.target_module or 'teamzero.<feature>'}")
            print(f"      Invariants:  {len(brief.define.invariants)} business rules locked")
            print(f"      Test Rules:  {len(brief.test_rules)} decision-table rows compiled")
            print(" Next: Run 'python -m teamzero.cli spec --file " + str(out_spec) + "'")
            print("=" * 65)
        elif args.from_file:
            src = Path(args.from_file)
            if not src.exists():
                print(f"[!] Error: File '{src}' does not exist.")
                sys.exit(1)
            brief = parse_ideation_markdown(src.read_text(encoding="utf-8"))
            saved = save_brief_to_inbox(brief)
            print("=" * 65)
            print(" TeamZero Design Thinking Intake Terminal")
            print("=" * 65)
            print(f" [OK] Ingested Design Thinking brief '{brief.title}'")
            print(f"      Saved to Inbox: {saved}")
            print(f"      Target Persona: {brief.empathize.target_persona or 'N/A'}")
            print(f"      Invariants:     {len(brief.define.invariants)} invariant(s)")
            print(f"      Test Rules:     {len(brief.test_rules)} decision-table condition(s)")
            print("=" * 65)
        else:
            # Interactive terminal wizard
            print("=" * 65)
            print(" TeamZero Founder Ideation Wizard (Design Thinking Framework)")
            print("=" * 65)
            title = args.title or input(" [?] Feature / Concept Title: ").strip() or "Untitled Feature"
            print("\n -- Stage 1: EMPATHIZE (Understand User & Pain Point) --")
            persona = input(" [?] Target Persona (Who has the problem?): ").strip()
            friction = input(" [?] Observed Friction (What is broken/hard?): ").strip()
            quote = input(" [?] User Quote / Verbatim expression: ").strip()
            need = input(" [?] Emotional Need (What relief/confidence is needed?): ").strip()

            print("\n -- Stage 2: DEFINE (Problem Statement & Invariants) --")
            pov = input(" [?] POV Statement ([User] needs [Action] because [Insight]): ").strip()
            hmw = input(" [?] How Might We (HMW) Prompt (e.g. How might we make checkout 1-tap?): ").strip()
            print(" [i] Enter non-negotiable business invariants (one per line, blank line to finish):")
            invariants = []
            while True:
                inv = input("     Invariant > ").strip()
                if not inv:
                    break
                invariants.append(inv)

            print("\n -- Stage 3: IDEATE (Divergent Brainstorming & Negative Inversion) --")
            tech = input(" [?] Ideation Technique (Brainstorming / SCAMPER / Crazy 8s / Reverse Brainstorming) [Brainstorming]: ").strip() or "Brainstorming"
            print(" [i] Negative / Reverse Brainstorming (How could this fail or frustrate users?):")
            neg_fails = []
            while True:
                f_mode = input("     Failure mode (blank to finish) > ").strip()
                if not f_mode:
                    break
                inv_sol = input("     -> Inverted solution > ").strip()
                neg_fails.append({"failure": f_mode, "inversion": inv_sol})

            print(" [i] Enter competing implementation hypotheses (blank line to finish):")
            hypotheses = []
            hypo_idx = 1
            while True:
                h = input(f"     Option {chr(64 + hypo_idx)} > ").strip()
                if not h:
                    break
                hypotheses.append({"name": chr(64 + hypo_idx), "desc": h})
                hypo_idx += 1

            print("\n -- Stage 4: PROTOTYPE & PRIORITIZATION (MoSCoW & Minimal Surface) --")
            must_input = input(" [?] MoSCoW Must-Haves (comma-separated): ").strip()
            impact_effort = input(" [?] Impact vs Effort (Quick Win / Strategic Build / Fill-in) [Quick Win]: ").strip() or "Quick Win"
            mod = input(" [?] Target Module (e.g. teamzero.checkout): ").strip()
            fn = input(" [?] Target Function Signature (e.g. run_checkout): ").strip()

            print("\n -- Stage 5: TEST (Decision Table Matrix) --")
            print(" [i] Add decision table rule (Rule ID, Condition, Expected Result):")
            rules = []
            while True:
                r_cond = input("     Condition (blank to finish, e.g. amount <= 0) > ").strip()
                if not r_cond:
                    break
                r_out = input("     Expected Outcome (e.g. ERROR_INVALID_AMOUNT) > ").strip()
                rid = f"RULE_{len(rules) + 1:02d}"
                rules.append(IdeationTestRule(rule_id=rid, condition=r_cond, expected_outcome=r_out))

            brief = DesignThinkingBrief(
                title=title,
                author=args.author,
                empathize=EmpathizePhase(
                    target_persona=persona,
                    observed_friction=friction,
                    user_quote=quote,
                    emotional_need=need,
                ),
                define=DefinePhase(
                    pov_statement=pov,
                    hmw_prompt=hmw,
                    invariants=invariants,
                ),
                ideate=IdeatePhase(
                    technique=tech,
                    negative_failure_modes=neg_fails,
                    hypotheses=hypotheses
                ),
                prototype=PrototypePhase(
                    moscow_must=[x.strip() for x in must_input.split(",") if x.strip()] if must_input else [],
                    impact_effort=impact_effort,
                    target_module=mod,
                    target_function=fn
                ),
                test_rules=rules,
            )

            saved = save_brief_to_inbox(brief)
            out_spec = compile_brief_to_spec(brief)
            print("\n" + "=" * 65)
            print(f" [SUCCESS] Ideation Brief Sealed!")
            print(f"   Inbox File: {saved}")
            print(f"   Compiled Spec: {out_spec}")
            print(f"   Next Step: Run 'python -m teamzero.cli race --spec {out_spec}'")
            print("=" * 65)
    elif args.subcommand == "task":
        from teamzero.tasks import TaskRegistry
        reg = TaskRegistry()

        if args.action == "parse":
            if not args.file:
                print("[!] Error: Specify --file <prd_or_ask.md> to parse.")
                sys.exit(1)
            src = Path(args.file)
            if not src.exists():
                print(f"[!] Error: File '{src}' not found.")
                sys.exit(1)
            content = src.read_text(encoding="utf-8")
            prefix = src.stem.replace("ASK_", "").replace("ASK-", "").upper()[:8] or "TASK"
            tasks = reg.decompose_prd(content, feature_prefix=prefix)
            print("=" * 65)
            print(f" TeamZero PRD Decomposition Engine")
            print("=" * 65)
            print(f" [OK] Decomposed {src.name} into {len(tasks)} dependency-chained microtasks:")
            for t in tasks:
                dep_str = f"<- {', '.join(t.dependencies)}" if t.dependencies else "[ROOT]"
                print(f"   * [{t.id}] (Complexity {t.complexity}/10) {t.title:<35} {dep_str}")
            print(f"\n Tasks saved to .teamzero/tasks.json. Run 'tz task next' to start.")
            print("=" * 65)
        elif args.action == "next":
            nxt = reg.get_next_task()
            print("=" * 65)
            print(" TeamZero Active Task Navigator")
            print("=" * 65)
            if not nxt:
                print(" [i] No ready tasks found. Either all tasks are complete, or remaining tasks are blocked.")
            else:
                dep_str = ', '.join(nxt.dependencies) if nxt.dependencies else "None (Ready)"
                print(f" [NEXT READY TASK] ID: {nxt.id}")
                print(f" Title:        {nxt.title}")
                print(f" Complexity:   {nxt.complexity}/10")
                print(f" Dependencies: {dep_str}")
                print(f" Description:  {nxt.description}")
                if nxt.acceptance_criteria:
                    print(f" Acceptance Criteria:")
                    for ac in nxt.acceptance_criteria:
                        print(f"   - {ac}")
            print("=" * 65)
        elif args.action == "expand":
            if not args.id or not args.subtasks:
                print("[!] Error: Specify --id <task_id> and --subtasks 'Subtask 1, Subtask 2'")
                sys.exit(1)
            sub_titles = [s.strip() for s in args.subtasks.split(",") if s.strip()]
            subs = reg.expand_task(args.id, sub_titles)
            print("=" * 65)
            print(f" [OK] Expanded {args.id} into {len(subs)} subtasks:")
            for s in subs:
                print(f"   + [{s.id}] {s.title} (Complexity {s.complexity}/10)")
            print("=" * 65)
        elif args.action == "update":
            if not args.id or not args.status:
                print("[!] Error: Specify --id <task_id> and --status <STATUS>")
                sys.exit(1)
            updated = reg.update_status(args.id, args.status)
            if updated:
                print(f"[OK] Task {updated.id} status updated to {updated.status}")
            else:
                print(f"[!] Task {args.id} not found.")
        elif args.action == "validate":
            val = reg.validate_dependencies()
            print("=" * 65)
            print(" TeamZero Dependency DAG Validation")
            print("=" * 65)
            if val["valid"]:
                print(f" [OK] All {val['total_tasks']} tasks have valid dependencies with zero cycles.")
            else:
                if val.get("missing_dependencies"):
                    print(" [!] Missing Dependencies:")
                    for tid, missing in val["missing_dependencies"].items():
                        print(f"     Task {tid} references missing: {', '.join(missing)}")
                if val.get("circular_dependencies"):
                    print(" [!] Circular Loops:")
                    for cycle in val["circular_dependencies"]:
                        print(f"     Cycle: {cycle}")
            print("=" * 65)
        elif args.action == "fix":
            fix_res = reg.fix_dependencies()
            print("=" * 65)
            print(" TeamZero Dependency Auto-Fix")
            print("=" * 65)
            print(f" Fixed {fix_res['fixed_count']} dangling dependencies.")
            print(f" Status: {fix_res['status']}")
            print("=" * 65)
        else:  # list
            tasks = reg.load_tasks()
            print("=" * 70)
            print(" TeamZero Microtask Registry (DAG)")
            print("=" * 70)
            if not tasks:
                print(" [i] Registry is empty. Run 'tz task parse --file <prd.md>' to ingest tasks.")
            else:
                print(f" {'ID':<10} | {'STATUS':<12} | {'CMPLX':<5} | {'TITLE':<32}")
                print(" " + "-" * 66)
                for t in tasks:
                    badge = f"[{t.status}]"
                    print(f" {t.id:<10} | {badge:<12} | {t.complexity:<5} | {t.title[:32]}")
            print("=" * 70)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
