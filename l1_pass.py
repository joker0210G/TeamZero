#!/usr/bin/env python3
"""TeamZero L1 Red Team Pass — "The Breaker Run"

Attacks a gauntlet-green merge candidate before it reaches the human founder.
Follows the cheapest-first ladder:
  A. Deterministic Heuristics ........ 0 tokens
  B. Mechanical Boundary Probes ...... 0 tokens (subprocess isolation)
  C. Semantic Mutation Attack ........ 0 LLM tokens (CPU execution)
  D. LLM Spec Prober ................. 1 budget-capped call (proposes; harness verifies)

Usage:
  python l1_pass.py --demo --offline
  python l1_pass.py --candidate <path_to_candidate.json>
  python l1_pass.py --candidate <path_to_candidate.json> --offline
"""

from __future__ import annotations
import argparse
import dataclasses
from dataclasses import dataclass, field, asdict
import hashlib
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from teamzero.config import (
    ORG_DIR,
    OPENROUTER_URL,
    PROBER_MODEL,
    PROBER_BUDGET,
    FINDINGS_DIR,
    ASKS_DIR
)
from teamzero.governance import (
    sign_receipt,
    update_trust_score,
    compute_evidence_weighted_trust_delta,
    record_payroll,
    load_constitution
)
from teamzero.evidence import EvidenceGraph

# ── Configuration Constants ──────────────────────────────────────────────────
PROBE_TIMEOUT_S = 5
MAX_MUTANTS = 10
MAX_REPAIRS = 3

RISK_PATTERNS = [
    r"\b(auth|password|token|secret|pay|price|charge|refund|round|expire|timeout|thread|lock|async|requests\.|http)\b",
]

SEMANTIC_MUTATIONS = [
    (" <= ", " < "),
    (" < ", " <= "),
    (" == ", " != "),
    (" != ", " == "),
    (" >= ", " > "),
    (" > ", " >= "),
    (".strip()", ""),
    (".lower()", ""),
    (" + 1", " - 1"),
    (" - 1", " + 1"),
    ("max(", "min("),
    ("min(", "max("),
    ("round(", "int("),
]

BOUNDARIES = {
    "int": [0, 1, -1, 29, 30, 31, 2147483647, -2147483648],
    "float": [0.0, 1.0, -1.0, 0.01, 100.0, -10.0, 1e6],
    "string": ["", " ", "null", "None", "0", "ünïcödé", "UNOPENED", "x" * 100],
    "bool": [True, False],
}

TRIVIAL_ASSERT_PATTERNS = [
    r"assert\s+True",
    r"assert\s+\w+\s+is not None",
    r"^\s*pass\s*$",
    r"expect\(.+\)\.toBeDefined\(\)"
]


@dataclass
class Finding:
    fid: str
    phase: str
    severity: str  # critical | high | medium | low
    title: str
    evidence: str
    repro: str = ""


# ── Subprocess Runner Helper ─────────────────────────────────────────────────
RUNNER_CODE = r'''
import json, sys, importlib.util

entry_file = sys.argv[1]
entry_fn = sys.argv[2]
args_json = sys.argv[3]

try:
    spec = importlib.util.spec_from_file_location("candidate_module", entry_file)
    if not spec or not spec.loader:
        print(json.dumps({"ok": False, "error": f"Failed to load spec for {entry_file}"}))
        sys.exit(0)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, entry_fn, None)
    if not fn:
        print(json.dumps({"ok": False, "error": f"Function {entry_fn} not found in {entry_file}"}))
        sys.exit(0)
        
    args = json.loads(args_json)
    res = fn(**args)
    print(json.dumps({"ok": True, "result": res}))
except Exception as e:
    print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {str(e)}"}))
'''


def execute_probe_subprocess(entry_file: str, entry_fn: str, args: dict) -> dict:
    """Executes a single probe in an isolated subprocess with hard timeout."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tf:
        tf.write(RUNNER_CODE)
        runner_path = tf.name

    try:
        cmd = [sys.executable, runner_path, entry_file, entry_fn, json.dumps(args)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=PROBE_TIMEOUT_S)
        if proc.returncode != 0:
            return {"ok": False, "error": proc.stderr.strip() or "Non-zero exit"}
        lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        for line in reversed(lines):
            try:
                return json.loads(line)
            except Exception:
                continue
        return {"ok": False, "error": "Empty or non-JSON output"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "TimeoutExpired (>5s)"}
    except Exception as e:
        return {"ok": False, "error": f"RunnerException: {e}"}
    finally:
        try:
            os.remove(runner_path)
        except Exception:
            pass


# ── Phase A: Deterministic Heuristics ─────────────────────────────────────────
def phase_a_deterministic_heuristics(candidate: dict) -> List[Finding]:
    """Runs zero-token static heuristics on spec, diff, and test coverage."""
    findings = []
    spec = candidate.get("spec", {})
    rules = spec.get("decision_table", [])
    tests = candidate.get("tests", [])
    diff = candidate.get("diff", "")

    # 1. Decision Table Coverage Audit
    covered_rules = set()
    for t in tests:
        for ref in t.get("references", []):
            covered_rules.add(ref)

    for r in rules:
        rid = r.get("id")
        if rid and rid not in covered_rules:
            findings.append(Finding(
                fid=f"DET-COV-{rid}",
                phase="Phase A (Deterministic)",
                severity="high",
                title=f"Rule {rid} lacks declared test coverage",
                evidence=f"Decision table rule '{r.get('description', '')}' is unreferenced in test suite.",
                repro=json.dumps({"uncovered_rule": rid})
            ))

    # 2. Assertion Strength Audit
    for t in tests:
        test_name = t.get("name", "unknown")
        assertions = t.get("assertions", 1)
        body = t.get("body", "")
        if assertions == 0:
            findings.append(Finding(
                fid=f"DET-ASSERT-ZERO-{test_name}",
                phase="Phase A (Deterministic)",
                severity="medium",
                title=f"Test '{test_name}' has zero assertions",
                evidence="Test execution registers 0 assertions. Risk: always-green dummy test."
            ))
        for pat in TRIVIAL_ASSERT_PATTERNS:
            if re.search(pat, body):
                findings.append(Finding(
                    fid=f"DET-ASSERT-TRIVIAL-{test_name}",
                    phase="Phase A (Deterministic)",
                    severity="low",
                    title=f"Test '{test_name}' contains trivial assertions",
                    evidence=f"Matched pattern: {pat}"
                ))

    # 3. Diff Risk Surface Check
    risk_hits = []
    for pat in RISK_PATTERNS:
        matches = re.findall(pat, diff, flags=re.IGNORECASE)
        if matches:
            risk_hits.extend(matches)
    if risk_hits:
        findings.append(Finding(
            fid="DET-RISK-SURFACE",
            phase="Phase A (Deterministic)",
            severity="low",
            title="Diff touches high-risk surface area",
            evidence=f"Tokens identified in diff: {sorted(list(set(risk_hits)))}"
        ))

    return findings


# ── Phase B: Mechanical Boundary Probes ───────────────────────────────────────
def generate_boundary_probes(candidate: dict) -> List[dict]:
    """Generates boundary probe vectors across the decision table edges."""
    spec = candidate.get("spec", {})
    rules = spec.get("decision_table", [])
    probes = []

    # Baseline representative values
    base_args = {"amount_paid": 50.0, "days_since_purchase": 10, "item_condition": "unopened"}

    for rule in rules:
        rid = rule.get("id")
        when = rule.get("when", {})
        then = rule.get("then", {})

        # Operator edge probes (<=, <, >=, >)
        days_cond = when.get("days_since_purchase", {})
        if isinstance(days_cond, dict) and "limit" in days_cond:
            lim = days_cond["limit"]
            for offset in [-1, 0, 1]:
                val = lim + offset
                probe_args = dict(base_args)
                probe_args["days_since_purchase"] = val
                if "item_condition" in when:
                    probe_args["item_condition"] = when["item_condition"].get("eq", "unopened")
                probes.append({
                    "id": f"PROBE-EDGE-{rid}-day{val}",
                    "rule_id": rid,
                    "args": probe_args,
                    "target_param": "days_since_purchase",
                    "expected_rule": then
                })

    # Sweep type boundaries
    for b_day in [-5, 0, 30, 31, 999]:
        for b_cond in ["unopened", "opened", "UNOPENED", ""]:
            for b_amt in [-10.0, 0.0, 100.0]:
                probes.append({
                    "id": f"PROBE-SWEEP-amt{b_amt}-d{b_day}-{b_cond}",
                    "rule_id": "GENERAL_SWEEP",
                    "args": {
                        "amount_paid": b_amt,
                        "days_since_purchase": b_day,
                        "item_condition": b_cond
                    },
                    "target_param": "multi",
                    "expected_rule": None
                })

    return probes


def check_probe_result(probe: dict, result: dict, spec: dict) -> List[Finding]:
    """Evaluates probe outcome against decision table expectations and global invariants."""
    findings = []
    pid = probe["id"]
    args = probe["args"]
    amt = args.get("amount_paid", 0.0)
    days = args.get("days_since_purchase", 0)
    cond = args.get("item_condition", "")

    # Crash check
    if not result.get("ok"):
        err = result.get("error", "")
        # If input was explicitly invalid (negative amount or days), ValueError is expected and safe
        if (amt < 0 or days < 0) and "ValueError" in err:
            return []  # Properly guarded!
        # Otherwise unexpected crash is a high finding
        findings.append(Finding(
            fid=f"PROBE-CRASH-{pid}",
            phase="Phase B (Probes)",
            severity="high",
            title=f"Unhandled crash on input: {err}",
            evidence=f"Call failed unexpectedly on args: {args}",
            repro=json.dumps({"args": args, "error": err})
        ))
        return findings

    ret = result.get("result", {})
    if not isinstance(ret, dict) or "refund" not in ret:
        findings.append(Finding(
            fid=f"PROBE-SCHEMA-{pid}",
            phase="Phase B (Probes)",
            severity="critical",
            title="Return payload does not conform to specification schema",
            evidence=f"Expected dict with 'refund' key, received: {ret}",
            repro=json.dumps({"args": args, "got": ret})
        ))
        return findings

    refund_val = ret["refund"]

    # Invariant Inviolability: Negative amounts or days MUST NOT yield refunds
    if amt < 0 and refund_val < 0:
        findings.append(Finding(
            fid=f"INV-NEGATIVE-REFUND-{pid}",
            phase="Phase B (Probes)",
            severity="critical",
            title="Invariant Violation: Unguarded negative input returns negative refund",
            evidence=f"amount_paid={amt} resulted in refund={refund_val}. Unsanitized reverse-charge risk!",
            repro=json.dumps({"args": args, "returned": ret})
        ))

    if amt >= 0 and refund_val < 0:
        findings.append(Finding(
            fid=f"INV-NEGATIVE-VAL-{pid}",
            phase="Phase B (Probes)",
            severity="critical",
            title="Invariant Violation: Refund value is negative for non-negative payment",
            evidence=f"refund={refund_val} < 0",
            repro=json.dumps({"args": args, "returned": ret})
        ))

    if amt >= 0 and refund_val > amt + 1e-4:
        findings.append(Finding(
            fid=f"INV-OVERPAY-{pid}",
            phase="Phase B (Probes)",
            severity="critical",
            title="Invariant Violation: Refund exceeds original payment",
            evidence=f"refund={refund_val} > amount_paid={amt}",
            repro=json.dumps({"args": args, "returned": ret})
        ))

    # Exact Decision Table Rule Divergence Check
    # Rule R1 Check at boundary: days <= 30 and unopened
    if 0 <= days <= 30 and cond == "unopened" and amt >= 0:
        expected_full = round(float(amt), 2)
        if abs(refund_val - expected_full) > 0.01:
            findings.append(Finding(
                fid=f"SPEC-DIVERGENCE-R1-day{days}",
                phase="Phase B (Probes)",
                severity="critical",
                title=f"Spec Divergence: Day {days} unopened received {refund_val}, expected full {expected_full}",
                evidence=f"Rule R1 specifies full refund within 30 days. Failed on boundary day {days}.",
                repro=json.dumps({"args": args, "expected": expected_full, "got": refund_val})
            ))

    return findings


# ── Phase C: Semantic Mutation Attack ─────────────────────────────────────────
def phase_c_mutation_attack(entry_file: str, entry_fn: str, probes: List[dict], baseline: List[dict]) -> List[Finding]:
    """Applies high-priority semantic operator mutations and checks for probe survival."""
    findings = []
    try:
        with open(entry_file, "r", encoding="utf-8") as f:
            src = f.read()
    except Exception:
        return []

    mutant_count = 0
    survivors = []

    for old_op, new_op in SEMANTIC_MUTATIONS:
        if mutant_count >= MAX_MUTANTS:
            break
        for match in re.finditer(re.escape(old_op), src):
            if mutant_count >= MAX_MUTANTS:
                break
            mutant_src = src[:match.start()] + new_op + src[match.end():]
            
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tf:
                tf.write(mutant_src)
                mutant_path = tf.name

            try:
                # Test whether mutant survives (all probe results match baseline)
                all_equal = True
                for i, p in enumerate(probes[:15]):  # Run subset for CPU budget
                    base_res = baseline[i]
                    mut_res = execute_probe_subprocess(mutant_path, entry_fn, p["args"])
                    if mut_res != base_res:
                        all_equal = False
                        break  # Mutant killed!

                if all_equal:
                    survivors.append(f"Mutant '{old_op.strip()}' -> '{new_op.strip()}' survived all test probes.")
            finally:
                try:
                    os.remove(mutant_path)
                except Exception:
                    pass
            mutant_count += 1

    if survivors:
        for s in survivors:
            findings.append(Finding(
                fid=f"MUT-SURVIVOR-{hashlib.md5(s.encode()).hexdigest()[:8]}",
                phase="Phase C (Mutations)",
                severity="medium",
                title="Semantic Mutant Survived Probing",
                evidence=f"{s} (Exposes potential test assertion blind spot)"
            ))

    return findings


# ── Phase D: LLM Spec Prober ──────────────────────────────────────────────────
PROBER_ROLE_CARD = """You are BREAKER, TeamZero's adversarial reviewer. Different model family from the author.
Mission: prove this candidate is NOT done.
You receive: spec, diff, and existing test names.
Attack priority: boundary values, unguarded inputs (negative/empty/NaN/huge), timezones, authorization, spec silence.
Output STRICT JSON array, max 3 items:
[{"attack": "...", "input": {"param": value}, "expected": "...", "risk": "...", "severity": "critical|high|medium"}]
If no flaws found, return empty array []. No markdown formatting outside JSON.
"""


def phase_d_llm_spec_prober(candidate: dict, offline: bool = False) -> Tuple[List[Finding], int]:
    """Executes budget-governed LLM prober call and mechanically validates proposed hypotheses."""
    if offline:
        return [], 0

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        return [], 0

    spec = candidate.get("spec", {})
    diff = candidate.get("diff", "")
    tests = [t.get("name") for t in candidate.get("tests", [])]

    user_prompt = f"""Spec:
{json.dumps(spec, indent=2)}

Candidate Diff:
{diff}

Existing Tests:
{tests}
"""

    payload = {
        "model": PROBER_MODEL,
        "messages": [
            {"role": "system", "content": PROBER_ROLE_CARD},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 600
    }

    tokens_used = 0
    try:
        req = urllib.request.Request(
            OPENROUTER_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            tokens_used = data.get("usage", {}).get("total_tokens", 800)
            content = data["choices"][0]["message"]["content"]
            
            # Clean markdown code fences
            cleaned = re.sub(r"^```(json)?|```$", "", content.strip(), flags=re.MULTILINE).strip()
            hypotheses = json.loads(cleaned)
    except Exception:
        return [], tokens_used

    findings = []
    if isinstance(hypotheses, list):
        entry_file = candidate.get("entry", {}).get("file", "")
        entry_fn = candidate.get("entry", {}).get("function", "")
        for h in hypotheses:
            inp = h.get("input", {})
            if isinstance(inp, dict):
                # Verify hypothesis mechanically in subprocess
                res = execute_probe_subprocess(entry_file, entry_fn, inp)
                is_crash = not res.get("ok")
                findings.append(Finding(
                    fid=f"LLM-PROBER-{hashlib.md5(h.get('attack','').encode()).hexdigest()[:8]}",
                    phase="Phase D (LLM Prober)",
                    severity=h.get("severity", "medium"),
                    title=f"Adversarial Prober Finding: {h.get('attack')}",
                    evidence=f"Proposed risk: {h.get('risk')} | Mechanical verification: {'Triggered Crash' if is_crash else 'Observed: ' + str(res.get('result'))}",
                    repro=json.dumps({"input": inp, "result": res})
                ))

    return findings, tokens_used


# ── Packet & Verdict Formulation ──────────────────────────────────────────────
def run_l1_breaker(candidate: dict, offline: bool = False) -> Dict[str, Any]:
    """Main orchestration loop for the L1 Breaker Pass."""
    start_time = time.time()
    task_id = candidate.get("task_id", f"TASK-{int(start_time)}")
    sha = candidate.get("commit_sha", hashlib.sha256(str(time.time()).encode()).hexdigest())[:12]
    author_agent = candidate.get("author_agent", "unknown")
    entry_file = candidate.get("entry", {}).get("file", "")
    entry_fn = candidate.get("entry", {}).get("function", "")

    all_findings: List[Finding] = []

    # Phase A
    findings_a = phase_a_deterministic_heuristics(candidate)
    all_findings.extend(findings_a)

    # Phase B
    probes = generate_boundary_probes(candidate)
    baseline_results = []
    for p in probes:
        res = execute_probe_subprocess(entry_file, entry_fn, p["args"])
        baseline_results.append(res)
        f_b = check_probe_result(p, res, candidate.get("spec", {}))
        all_findings.extend(f_b)

    # Phase C
    findings_c = phase_c_mutation_attack(entry_file, entry_fn, probes, baseline_results)
    all_findings.extend(findings_c)

    # Phase D (Risk gated)
    has_risk = any(f.fid == "DET-RISK-SURFACE" for f in findings_a)
    tokens_used = 0
    if has_risk and not offline:
        findings_d, tokens_used = phase_d_llm_spec_prober(candidate, offline=offline)
        all_findings.extend(findings_d)

    # Compute Verdict
    criticals = [f for f in all_findings if f.severity == "critical"]
    highs = [f for f in all_findings if f.severity == "high"]
    mediums = [f for f in all_findings if f.severity == "medium"]

    repair_attempts = candidate.get("repair_attempts", 0)

    if criticals or highs:
        if repair_attempts < MAX_REPAIRS:
            verdict = "NEEDS_REPAIR"
        else:
            verdict = "ESCALATE_FOUNDER"
    else:
        verdict = "PASS"

    # Governance & Trust Updates ( Evidence-Weighted Trust Decay)
    ev_graph_lookup = EvidenceGraph()
    if verdict == "PASS":
        update_trust_score(author_agent, delta=+2, reason=f"Breaker PASS on {sha[:8]}")
    else:
        findings_dicts = [asdict(f) for f in all_findings]
        delta, reason_str = compute_evidence_weighted_trust_delta(findings_dicts, ev_graph_lookup)
        if verdict == "ESCALATE_FOUNDER":
            delta -= 5  # Additional penalty for exhausting repair attempts
            reason_str += f" [Max repairs exceeded on {sha[:8]}]"
        else:
            reason_str += f" [Breaker caught defects on {sha[:8]}]"
        update_trust_score(author_agent, delta=delta, reason=reason_str)

    record_payroll(task_id, author_agent, tokens_used, cost_usd=tokens_used * 0.000001)
    receipt_data = sign_receipt(f"{task_id}:{sha}", "breaker_run")

    findings_packet = {
        "task_id": task_id,
        "commit_sha": sha,
        "verdict": verdict,
        "summary": {
            "total_findings": len(all_findings),
            "critical": len(criticals),
            "high": len(highs),
            "medium": len(mediums),
            "low": len(all_findings) - len(criticals) - len(highs) - len(mediums),
        },
        "receipt": receipt_data["receipt"],
        "issued_at": receipt_data["issued_at"],
        "token_usage": tokens_used,
        "findings": [asdict(f) for f in all_findings]
    }

    # Persist findings packet
    FINDINGS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = FINDINGS_DIR / f"{task_id}_{sha[:8]}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(findings_packet, f, indent=2)

    # Record into Typed Evidence Graph 
    ev_graph = EvidenceGraph()
    task_gen = candidate.get("generation", 1)
    if all_findings:
        for f in all_findings:
            ev_graph.record_finding(
                task_id=task_id,
                commit_sha=sha,
                generation=task_gen,
                finding_dict=asdict(f),
                cost_tokens=tokens_used
            )
    elif verdict == "PASS":
        # Candidate is clean on this task - mark past open nodes for this task as resolved
        for node in ev_graph.list_nodes(task_id=task_id, status="OPEN"):
            ev_graph.mark_resolved(node.node_id, resolved_by_commit=sha)

    # Escalate if needed
    if verdict == "ESCALATE_FOUNDER":
        ASKS_DIR.mkdir(parents=True, exist_ok=True)
        ask_file = ASKS_DIR / f"ask_{task_id}_{sha[:8]}.json"
        with open(ask_file, "w", encoding="utf-8") as f:
            json.dump({
                "type": "BREAKER_ESCALATION",
                "task_id": task_id,
                "commit_sha": sha,
                "reason": "Candidate failed verification after maximum repair attempts",
                "findings": [asdict(f) for f in criticals + highs]
            }, f, indent=2)

    return findings_packet


# ── Demo Mode Setup ───────────────────────────────────────────────────────────
DEMO_BUGGY_IMPL = r'''
def calculate_refund(amount_paid, days_since_purchase, item_condition):
    """Buggy demo implementation seeded with classic AI slop errors:
    1. Off-by-one boundary: '< 30' instead of '<= 30' on Day 30 unopened.
    2. Unguarded negative input: does not validate amount_paid < 0.
    """
    if days_since_purchase < 30 and item_condition == "unopened":
        return {"refund": float(amount_paid), "rule_id": "R1"}

    if days_since_purchase < 30 and item_condition == "opened":
        return {"refund": round(float(amount_paid) * 0.8, 2), "rule_id": "R2"}

    return {"refund": 0.0, "rule_id": "R3"}
'''


def run_demo():
    print("=" * 70)
    print(" TeamZero L1 Red Team Pass — DEMO MODE (Offline, 0 Tokens)")
    print("=" * 70)

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tf:
        tf.write(DEMO_BUGGY_IMPL)
        demo_file = tf.name

    demo_candidate = {
        "task_id": "DEMO-TASK-REFUND-001",
        "commit_sha": "a1b2c3d4e5f6",
        "author_agent": "engineer:demo-agent",
        "entry": {
            "file": demo_file,
            "function": "calculate_refund"
        },
        "diff": """
+def calculate_refund(amount_paid, days_since_purchase, item_condition):
+    # Process refund payment calculation
+    if days_since_purchase < 30 and item_condition == "unopened":
+        return {"refund": float(amount_paid), "rule_id": "R1"}
""",
        "spec": {
            "decision_table": [
                {
                    "id": "R1",
                    "description": "Unopened item <= 30 days receives full refund",
                    "when": {"days_since_purchase": {"op": "<=", "limit": 30}, "item_condition": {"eq": "unopened"}},
                    "then": {"refund_multiple": 1.0}
                },
                {
                    "id": "R2",
                    "description": "Opened item <= 30 days receives 80% refund",
                    "when": {"days_since_purchase": {"op": "<=", "limit": 30}, "item_condition": {"eq": "opened"}},
                    "then": {"refund_multiple": 0.8}
                },
                {
                    "id": "R3",
                    "description": "Purchases > 30 days expired",
                    "when": {"days_since_purchase": {"op": ">", "limit": 30}},
                    "then": {"refund_multiple": 0.0}
                }
            ]
        },
        "tests": [
            {"name": "test_r1_standard", "references": ["R1"], "assertions": 1, "body": "assert res['refund'] == 100"},
            {"name": "test_r2_opened", "references": ["R2"], "assertions": 1, "body": "assert res['refund'] == 80"},
            {"name": "test_r3_dummy", "references": ["R3"], "assertions": 0, "body": "pass"}  # Zero assertions!
        ],
        "repair_attempts": 0
    }

    try:
        packet = run_l1_breaker(demo_candidate, offline=True)
        print("\n>>> Breaker Run Complete <<<")
        print(f"Verdict:       {packet['verdict']}")
        print(f"Receipt:       {packet['receipt']}")
        print(f"Summary:       {packet['summary']}")
        print("\nIdentified Findings:")
        for f in packet["findings"]:
            print(f" - [{f['severity'].upper()}] ({f['phase']}) {f['title']}")
            print(f"   Evidence: {f['evidence']}")
            if f["repro"]:
                print(f"   Repro:    {f['repro']}")
        print("\n" + "=" * 70)
    finally:
        try:
            os.remove(demo_file)
        except Exception:
            pass


def assemble_live_candidate() -> dict:
    """Assembles a real candidate manifest from the active repository state."""
    spec_path = Path(".teamzero/memory/specs/refund_spec.json")
    spec_data = {}
    if spec_path.exists():
        spec_data = json.loads(spec_path.read_text(encoding="utf-8"))

    # Determine git SHA
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        sha = "000000000000"

    # Git diff of recent changes
    diff_text = ""
    try:
        diff_res = subprocess.run(["git", "diff", "HEAD~1", "HEAD"], capture_output=True, text=True)
        diff_text = diff_res.stdout
    except Exception:
        pass

    target_file = Path("teamzero/refund_service.py").resolve()

    return {
        "task_id": f"TASK-LIVE-{sha[:8]}",
        "commit_sha": sha,
        "author_agent": "git:author",
        "entry": {
            "file": str(target_file),
            "function": "calculate_refund"
        },
        "diff": diff_text or "+# Live repository code verification",
        "spec": spec_data,
        "tests": [
            {"name": "test_r1_unopened", "references": ["R1"], "assertions": 3},
            {"name": "test_r2_opened", "references": ["R2"], "assertions": 2},
            {"name": "test_r3_past", "references": ["R3"], "assertions": 2}
        ],
        "repair_attempts": 0
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TeamZero L1 Red Team Pass")
    parser.add_argument("--demo", action="store_true", help="Run self-contained offline demonstration")
    parser.add_argument("--offline", action="store_true", help="Force offline mode (skip LLM prober calls)")
    parser.add_argument("--candidate", type=str, help="Path to JSON candidate manifest")
    parser.add_argument("--live", action="store_true", help="Run against active repository candidate code")
    args = parser.parse_args()

    if args.demo:
        run_demo()
    elif args.candidate:
        with open(args.candidate, "r", encoding="utf-8") as f:
            cand_data = json.load(f)
        res = run_l1_breaker(cand_data, offline=args.offline)
        print(json.dumps(res, indent=2))
        if res.get("verdict") != "PASS":
            sys.exit(1)
    else:
        # Default in CI and standard invocation: Evaluate LIVE code, not demo fixture!
        print("[*] Running L1 Breaker on live repository candidate code...")
        cand_data = assemble_live_candidate()
        res = run_l1_breaker(cand_data, offline=args.offline)
        print(f"\n[Breaker Verdict] {res['verdict']}")
        print(f"Receipt: {res['receipt']}")
        print(f"Summary: {res['summary']}")
        if res.get("verdict") != "PASS":
            print(f"\n[!] BREAKER BLOCKED: Candidate contains {res['summary'].get('critical', 0)} critical defects.")
            sys.exit(1)
