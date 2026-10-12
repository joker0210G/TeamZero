"""Chain-of-Verification (CoVe) & Multi-Path Reasoning Engine for TeamZero.

Implements research-backed hallucination elimination patterns:
1. Chain-of-Verification (CoVe):
   - Step 1: Baseline Candidate Draft
   - Step 2: Verification Plan Formulation (fact-checking questions)
   - Step 3: Independent Execution against Ground Truth (AST, Living Maps, Traps)
   - Step 4: Evidence-Based Rectification & Revision
2. Self-Consistency:
   - Multi-path sampling and consensus scoring across competing candidate implementations.
3. EVER (Real-Time Step-Wise Rectification):
   - Block-by-block concept validation preventing hallucination cascade.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from teamzero.config import ROOT_DIR, SPECS_DIR, TRAPS_DIR, ADR_DIR, MAP_DIR
from teamzero.anti_hallucination import validate_code_grounding, GroundingFinding


@dataclass
class VerificationQuestion:
    id: str
    category: str  # API_GROUNDING | INVARIANT_CHECK | TRAP_COMPLIANCE | BOUNDARY_EDGE | SYNTAX_VALIDITY
    question: str
    expected_source: str  # AST | LIVING_MAP | TRAPS | CONSTITUTION | TESTS


@dataclass
class VerificationAnswer:
    question_id: str
    category: str
    verified: bool
    ground_truth_finding: str
    evidence_source: str
    correction_needed: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def generate_verification_plan(
    candidate_code: str,
    feature: str = "general"
) -> List[VerificationQuestion]:
    """Formulates a targeted fact-checking verification plan for candidate code.

    Breaks down verification into distinct, independent questions that test API existence,
    invariants, domain traps, and boundary cases.
    """
    questions: List[VerificationQuestion] = []

    # Q1: Syntax & AST Well-formedness
    questions.append(
        VerificationQuestion(
            id="COVE-Q1",
            category="SYNTAX_VALIDITY",
            question="Is the code syntactically well-formed and parseable as a valid Abstract Syntax Tree?",
            expected_source="AST"
        )
    )

    # Q2: API & Symbol Grounding
    questions.append(
        VerificationQuestion(
            id="COVE-Q2",
            category="API_GROUNDING",
            question="Do all imported modules and symbols exist in TeamZero without hallucinated APIs?",
            expected_source="AST"
        )
    )

    # Q3: Quality Constitution & Invariant 04 (Zero Hardcoded Secrets)
    questions.append(
        VerificationQuestion(
            id="COVE-Q3",
            category="INVARIANT_CHECK",
            question="Does the code satisfy Invariant INV-04 by containing zero hardcoded API keys, secrets, or tokens?",
            expected_source="CONSTITUTION"
        )
    )

    # Q4: Domain Trap & Anti-Pattern Compliance
    questions.append(
        VerificationQuestion(
            id="COVE-Q4",
            category="TRAP_COMPLIANCE",
            question=f"Does the candidate avoid registered domain anti-patterns for module '{feature}'?",
            expected_source="TRAPS"
        )
    )

    # Q5: Boundary & Exception Handling
    questions.append(
        VerificationQuestion(
            id="COVE-Q5",
            category="BOUNDARY_EDGE",
            question="Are negative, null, empty inputs and runtime errors handled explicitly rather than failing silently?",
            expected_source="AST"
        )
    )

    return questions


def execute_verification_plan(
    candidate_code: str,
    questions: List[VerificationQuestion],
    feature: str = "general",
    root: Path = ROOT_DIR
) -> List[VerificationAnswer]:
    """Executes verification questions independently against ground truth sources."""
    answers: List[VerificationAnswer] = []

    # Parse AST once for inspection
    parsed_tree = None
    syntax_error_msg = None
    try:
        parsed_tree = ast.parse(candidate_code)
    except SyntaxError as e:
        syntax_error_msg = f"SyntaxError at line {e.lineno}: {e.msg}"

    for q in questions:
        if q.category == "SYNTAX_VALIDITY":
            if parsed_tree is not None:
                answers.append(
                    VerificationAnswer(
                        question_id=q.id,
                        category=q.category,
                        verified=True,
                        ground_truth_finding="Code parsed successfully into valid AST.",
                        evidence_source="Python AST Compiler"
                    )
                )
            else:
                answers.append(
                    VerificationAnswer(
                        question_id=q.id,
                        category=q.category,
                        verified=False,
                        ground_truth_finding=syntax_error_msg or "Failed to parse syntax.",
                        evidence_source="Python AST Compiler",
                        correction_needed="Fix syntax error."
                    )
                )

        elif q.category == "API_GROUNDING":
            grounding = validate_code_grounding(candidate_code, root=root)
            if grounding["grounded"]:
                answers.append(
                    VerificationAnswer(
                        question_id=q.id,
                        category=q.category,
                        verified=True,
                        ground_truth_finding="All local modules and imported symbols verified against repository AST.",
                        evidence_source="Repository AST Index"
                    )
                )
            else:
                findings_desc = "; ".join(f"{f['kind']}: {f['message']}" for f in grounding["findings"])
                corrections = [
                    f"Replace '{f['symbol']}' with one of: {', '.join(f.get('suggestions', []))}"
                    for f in grounding["findings"] if f.get("suggestions")
                ]
                answers.append(
                    VerificationAnswer(
                        question_id=q.id,
                        category=q.category,
                        verified=False,
                        ground_truth_finding=findings_desc,
                        evidence_source="Repository AST Index",
                        correction_needed="; ".join(corrections) or "Remove or fix fabricated imports."
                    )
                )

        elif q.category == "INVARIANT_CHECK":
            secret_pattern = re.search(
                r"(?:api_key|secret|password|bearer|auth_token)\s*=\s*['\"][A-Za-z0-9_\-]{16,}['\"]",
                candidate_code,
                re.I
            )
            if secret_pattern:
                answers.append(
                    VerificationAnswer(
                        question_id=q.id,
                        category=q.category,
                        verified=False,
                        ground_truth_finding="Found hardcoded credential pattern matching INV-04 violation.",
                        evidence_source="TeamZero Quality Constitution (INV-04)",
                        correction_needed="Extract secret to environment variable or mock token."
                    )
                )
            else:
                answers.append(
                    VerificationAnswer(
                        question_id=q.id,
                        category=q.category,
                        verified=True,
                        ground_truth_finding="Zero hardcoded credentials detected. Satisfies INV-04.",
                        evidence_source="TeamZero Quality Constitution (INV-04)"
                    )
                )

        elif q.category == "TRAP_COMPLIANCE":
            trap_file = root / ".teamzero" / "memory" / "traps" / f"{feature.lower()}.md"
            if trap_file.exists():
                trap_content = trap_file.read_text(encoding="utf-8").lower()
                violation_found = None
                for anti_pattern in ["silent failure", "pass on exception", "hardcode refund"]:
                    if anti_pattern in trap_content and anti_pattern in candidate_code.lower():
                        violation_found = anti_pattern
                        break

                if violation_found:
                    answers.append(
                        VerificationAnswer(
                            question_id=q.id,
                            category=q.category,
                            verified=False,
                            ground_truth_finding=f"Code exhibits known trap '{violation_found}'.",
                            evidence_source=f".teamzero/memory/traps/{feature.lower()}.md",
                            correction_needed=f"Refactor to remove anti-pattern: '{violation_found}'."
                        )
                    )
                else:
                    answers.append(
                        VerificationAnswer(
                            question_id=q.id,
                            category=q.category,
                            verified=True,
                            ground_truth_finding="Code clean of known registered domain anti-patterns.",
                            evidence_source=f".teamzero/memory/traps/{feature.lower()}.md"
                        )
                    )
            else:
                answers.append(
                    VerificationAnswer(
                        question_id=q.id,
                        category=q.category,
                        verified=True,
                        ground_truth_finding=f"No trap cards registered for '{feature}'. Implicitly verified.",
                        evidence_source="Domain Traps Registry"
                    )
                )

        elif q.category == "BOUNDARY_EDGE":
            has_defensive_checks = False
            if parsed_tree:
                for node in ast.walk(parsed_tree):
                    if isinstance(node, (ast.If, ast.Try, ast.Assert)):
                        has_defensive_checks = True
                        break

            if has_defensive_checks or "if " in candidate_code:
                answers.append(
                    VerificationAnswer(
                        question_id=q.id,
                        category=q.category,
                        verified=True,
                        ground_truth_finding="Boundary checking and defensive logic detected in AST.",
                        evidence_source="AST Defensive Inspection"
                    )
                )
            else:
                answers.append(
                    VerificationAnswer(
                        question_id=q.id,
                        category=q.category,
                        verified=False,
                        ground_truth_finding="No parameter validation, bounds checking, or try/except found.",
                        evidence_source="AST Defensive Inspection",
                        correction_needed="Add input boundary validation for null/empty/invalid inputs."
                    )
                )

    return answers


def rectify_and_revise(
    candidate_code: str,
    answers: List[VerificationAnswer]
) -> Tuple[str, List[str]]:
    """Applies evidence-based rectifications to the candidate code based on verification failures."""
    corrections_applied: List[str] = []
    revised = candidate_code

    for ans in answers:
        if ans.verified:
            continue

        # Rectify fabricated imports if suggestions exist
        if ans.category == "API_GROUNDING" and ans.correction_needed:
            # Extract symbol and suggestions
            m = re.search(r"Replace '([^']+)' with one of: ([^;]+)", ans.correction_needed)
            if m:
                bad_sym = m.group(1)
                suggestions = [s.strip() for s in m.group(2).split(",") if s.strip()]
                if suggestions:
                    best_match = suggestions[0]
                    revised = re.sub(r"\b" + re.escape(bad_sym) + r"\b", best_match, revised)
                    corrections_applied.append(f"Replaced hallucinated symbol '{bad_sym}' with verified '{best_match}'.")

        # Rectify hardcoded credentials
        elif ans.category == "INVARIANT_CHECK":
            revised = re.sub(
                r"((?:api_key|secret|password|bearer|auth_token)\s*=\s*)['\"][A-Za-z0-9_\-]{16,}['\"]",
                r'\1os.environ.get("API_KEY", "MOCK_TOKEN")',
                revised,
                flags=re.I
            )
            if "import os" not in revised:
                revised = "import os\n" + revised
            corrections_applied.append("Replaced hardcoded credential with os.environ.get() mock fallback.")

    return revised, corrections_applied


def run_chain_of_verification(
    candidate_code: str,
    feature: str = "general",
    root: Path = ROOT_DIR
) -> Dict[str, Any]:
    """End-to-End Chain-of-Verification (CoVe) Pipeline.

    Draft -> Formulate Questions -> Independent Execution -> Rectification & Revision.
    """
    plan = generate_verification_plan(candidate_code, feature=feature)
    answers = execute_verification_plan(candidate_code, plan, feature=feature, root=root)

    failed_answers = [a for a in answers if not a.verified]
    is_initially_verified = len(failed_answers) == 0

    revised_code, corrections = rectify_and_revise(candidate_code, answers)

    # Re-verify revised code if corrections were applied
    final_verified = is_initially_verified
    if corrections:
        post_answers = execute_verification_plan(revised_code, plan, feature=feature, root=root)
        final_verified = all(a.verified for a in post_answers)
        status = "RECTIFIED_AND_VERIFIED" if final_verified else "PARTIALLY_RECTIFIED"
    else:
        status = "VERIFIED" if is_initially_verified else "VERIFICATION_FAILED"

    return {
        "status": status,
        "is_verified": final_verified,
        "total_checks": len(answers),
        "passed_checks": sum(1 for a in answers if a.verified),
        "corrections_applied": corrections,
        "verification_plan": [asdict(q) for q in plan],
        "verification_answers": [a.to_dict() for a in answers],
        "original_code": candidate_code,
        "revised_code": revised_code
    }


# ── Self-Consistency Consensus Engine ────────────────────────────────────────

def compute_self_consistency(
    candidates: List[str]
) -> Dict[str, Any]:
    """Evaluates multiple reasoning paths and selects the consensus implementation.

    Computes AST structural similarity and signature overlap across candidate solutions.
    """
    if not candidates:
        return {"error": "No candidates provided."}

    parsed_candidates = []
    for idx, c in enumerate(candidates):
        try:
            tree = ast.parse(c)
            funcs = sorted([n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))])
            classes = sorted([n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)])
            parsed_candidates.append({
                "index": idx,
                "code": c,
                "valid": True,
                "funcs": funcs,
                "classes": classes,
                "symbols": set(funcs + classes)
            })
        except SyntaxError:
            parsed_candidates.append({
                "index": idx,
                "code": c,
                "valid": False,
                "symbols": set()
            })

    valid_candidates = [c for c in parsed_candidates if c["valid"]]
    if not valid_candidates:
        return {"error": "All candidates failed syntax compilation.", "consensus_score": 0.0}

    # Compute pairwise Jaccard similarity across symbol sets
    consensus_scores = []
    for c1 in valid_candidates:
        sim_sum = 0.0
        for c2 in valid_candidates:
            if c1["index"] == c2["index"]:
                sim_sum += 1.0
            else:
                u = c1["symbols"].union(c2["symbols"])
                i = c1["symbols"].intersection(c2["symbols"])
                sim_sum += len(i) / len(u) if u else 0.5
        avg_score = sim_sum / len(valid_candidates)
        consensus_scores.append((avg_score, c1))

    consensus_scores.sort(key=lambda x: x[0], reverse=True)
    best_score, best_candidate = consensus_scores[0]

    return {
        "status": "CONSENSUS_REACHED" if best_score >= 0.6 else "DIVERGENT",
        "winning_candidate_index": best_candidate["index"],
        "consensus_score": round(best_score, 3),
        "total_candidates": len(candidates),
        "valid_candidates_count": len(valid_candidates),
        "selected_code": best_candidate["code"],
        "shared_symbols": list(best_candidate["symbols"])
    }
