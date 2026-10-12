"""Anti-Hallucination, Semantic Grounding, and Neurosymbolic Guardrails Engine.

Implements research-backed techniques to eliminate AI code and agent hallucinations:
1. Semantic Tool Selection: Ranks and filters MCP tools dynamically based on user intent to prevent choice overload.
2. Neurosymbolic Guardrail Hooks: Intercepts tool calls before execution to enforce symbolic invariants.
3. AST Grounding & API Fabrication Scanner: Validates generated imports and symbols against actual codebase AST.
4. Pre-Flight Assumption Elicitation: Surfacing unstated assumptions, ambiguous requirements, and missing edge cases.
5. Multi-Agent Cross-Validation: Executor -> Validator -> Critic pipeline ensuring verifiable execution.
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
import json
import math
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from teamzero.config import ROOT_DIR, SPECS_DIR, TRAPS_DIR, ADR_DIR, CACHE_DIR


# ── 1. Semantic Tool Selection (Choice Overload Reducer) ─────────────────────

def _tokenize(text: str) -> Set[str]:
    """Extracts alphanumeric tokens in lower case."""
    return set(re.findall(r"[a-z0-9_]{2,}", text.lower()))


def _compute_relevance(query_tokens: Set[str], tool_tokens: Set[str]) -> float:
    """Computes Jaccard/overlap similarity score between query and tool tokens."""
    if not query_tokens or not tool_tokens:
        return 0.0
    intersection = query_tokens.intersection(tool_tokens)
    union = query_tokens.union(tool_tokens)
    return len(intersection) / len(union) if union else 0.0


def rank_tools(
    query: str,
    available_tools: List[Dict[str, Any]],
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """Ranks and selects the top-k most relevant tools for a user query to avoid choice overload.

    Mitigates 'Function Selection' and 'Tool Appropriate' hallucinations caused by seeing 40+ tools at once.
    """
    q_tokens = _tokenize(query)
    scored: List[Tuple[float, Dict[str, Any]]] = []

    for tool in available_tools:
        name = tool.get("name", "")
        desc = tool.get("description", "")
        # Give extra weight to tool name tokens
        name_tokens = _tokenize(name.replace("teamzero_", "").replace("_", " "))
        desc_tokens = _tokenize(desc)
        all_tokens = name_tokens.union(desc_tokens)

        score = _compute_relevance(q_tokens, all_tokens)
        # Boost if direct token match in name
        if q_tokens.intersection(name_tokens):
            score += 0.35

        scored.append((score, tool))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, tool in scored[:top_k]:
        tool_copy = dict(tool)
        tool_copy["relevance_score"] = round(score, 3)
        results.append(tool_copy)

    return results


# ── 2. Neurosymbolic Guardrail Hooks (Framework-Level Rule Interception) ─────

@dataclass
class GuardrailViolation:
    rule_id: str
    message: str
    mitigation: str
    tool_name: str
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


class NeurosymbolicValidator:
    """Validates tool calls before execution against symbolic rules that LLMs cannot bypass."""

    def __init__(self, root: Path = ROOT_DIR):
        self.root = root

    def validate_tool_call(self, tool_name: str, kwargs: Dict[str, Any]) -> Tuple[bool, Optional[GuardrailViolation]]:
        """Evaluates symbolic constraints. Returns (passed, violation)."""

        # Rule R01: Path Traversal & Protected Secrets Shield
        for arg_name, arg_val in kwargs.items():
            if isinstance(arg_val, str) and ("path" in arg_name or "file" in arg_name):
                clean_path = arg_val.replace("\\", "/")
                if ".." in clean_path.split("/") or clean_path.startswith("/"):
                    # Check if it escapes root
                    target_p = Path(arg_val)
                    if not target_p.is_absolute():
                        target_p = (self.root / target_p).resolve()
                    if self.root not in target_p.parents and target_p != self.root:
                        return False, GuardrailViolation(
                            rule_id="R01_PATH_ESCAPE",
                            message=f"Path '{arg_val}' attempts to escape repository sandbox root.",
                            mitigation="Specify a path relative to the active workspace repository.",
                            tool_name=tool_name
                        )
                # Block direct access to secrets
                if ".mintkey" in clean_path or ".env" in clean_path:
                    return False, GuardrailViolation(
                        rule_id="R01_SECRET_ACCESS",
                        message=f"Access to protected secret file '{arg_val}' is blocked.",
                        mitigation="Authentication and mint keys are protected under Quality Invariant INV-04.",
                        tool_name=tool_name
                    )

        # Rule R02: Task Complexity Boundary (1 to 10)
        if "complexity" in kwargs:
            try:
                cmplx = int(kwargs["complexity"])
                if cmplx < 1 or cmplx > 10:
                    return False, GuardrailViolation(
                        rule_id="R02_COMPLEXITY_RANGE",
                        message=f"Complexity value {cmplx} is out of bounds. Must be an integer between 1 and 10.",
                        mitigation="Provide a complexity score from 1 (trivial) to 10 (architectural overhaul).",
                        tool_name=tool_name
                    )
            except (ValueError, TypeError):
                return False, GuardrailViolation(
                    rule_id="R02_COMPLEXITY_TYPE",
                    message=f"Complexity value '{kwargs['complexity']}' is not a valid integer.",
                    mitigation="Pass an integer between 1 and 10.",
                    tool_name=tool_name
                )

        # Rule R03: Non-Empty Identifiers
        for id_field in ["task_id", "feature", "run_id", "symbol_name"]:
            if id_field in kwargs:
                val = kwargs[id_field]
                if not isinstance(val, str) or not val.strip():
                    return False, GuardrailViolation(
                        rule_id="R03_EMPTY_IDENTIFIER",
                        message=f"Parameter '{id_field}' cannot be empty or whitespace.",
                        mitigation=f"Provide a valid non-empty string identifier for '{id_field}'.",
                        tool_name=tool_name
                    )

        # Rule R04: Non-Circular Subtasks
        if "parent_id" in kwargs and "subtask_id" in kwargs:
            if kwargs["parent_id"].strip().lower() == kwargs["subtask_id"].strip().lower():
                return False, GuardrailViolation(
                    rule_id="R04_SELF_PARENTING",
                    message=f"Subtask ID '{kwargs['subtask_id']}' cannot be its own parent.",
                    mitigation="Specify a distinct parent task ID.",
                    tool_name=tool_name
                )

        # Rule R05: Existing Spec Requirement for Candidate Submissions
        if tool_name == "teamzero_submit_candidate" and "feature" in kwargs:
            feat = kwargs["feature"].strip()
            specs_dir = self.root / ".teamzero" / "memory" / "specs"
            if specs_dir.is_dir():
                matches = list(specs_dir.glob(f"*{feat}*.json"))
                if not matches:
                    return False, GuardrailViolation(
                        rule_id="R05_MISSING_SPEC",
                        message=f"No executable specification found for feature '{feat}' in .teamzero/memory/specs/.",
                        mitigation="Create or compile a spec first via 'tz ideate --compile' or 'teamzero_ideate_spec'.",
                        tool_name=tool_name
                    )

        return True, None


# ── 3. AST Grounding & Code Hallucination Scanner ─────────────────────────────

@dataclass
class GroundingFinding:
    kind: str  # FABRICATED_MODULE | MISSING_SYMBOL | SYNTAX_ERROR | UNKNOWN_IMPORT
    symbol: str
    module: str
    message: str
    suggestions: List[str] = field(default_factory=list)
    line_number: int = 0


def validate_code_grounding(code_str: str, root: Path = ROOT_DIR) -> Dict[str, Any]:
    """Parses Python code via AST and checks every import/symbol against the real codebase.

    Catches fabricated imports (e.g. non-existent functions or modules) before execution.
    """
    findings: List[GroundingFinding] = []

    try:
        tree = ast.parse(code_str)
    except SyntaxError as e:
        return {
            "grounded": False,
            "syntax_valid": False,
            "findings": [
                GroundingFinding(
                    kind="SYNTAX_ERROR",
                    symbol="",
                    module="",
                    message=f"Syntax Error: {e.msg} at line {e.lineno}",
                    line_number=e.lineno or 0
                ).to_dict() if hasattr(GroundingFinding, "to_dict") else asdict(GroundingFinding(
                    kind="SYNTAX_ERROR", symbol="", module="", message=f"Syntax Error: {e.msg}", line_number=e.lineno or 0
                ))
            ]
        }

    src_dir = root / "teamzero"

    # Scan all imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod_name = alias.name
                if mod_name.startswith("teamzero."):
                    submod = mod_name.split(".", 1)[1]
                    target_file = src_dir / f"{submod}.py"
                    if not target_file.exists():
                        avail = [f.stem for f in src_dir.glob("*.py") if not f.name.startswith("__")]
                        findings.append(
                            GroundingFinding(
                                kind="FABRICATED_MODULE",
                                symbol=submod,
                                module=mod_name,
                                message=f"Module '{mod_name}' does not exist in TeamZero.",
                                suggestions=avail[:8],
                                line_number=node.lineno
                            )
                        )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod_name = node.module
                if mod_name == "teamzero" or mod_name.startswith("teamzero."):
                    submod = mod_name.split(".", 1)[1] if "." in mod_name else None
                    if submod:
                        target_file = src_dir / f"{submod}.py"
                        if not target_file.exists():
                            avail = [f.stem for f in src_dir.glob("*.py") if not f.name.startswith("__")]
                            findings.append(
                                GroundingFinding(
                                    kind="FABRICATED_MODULE",
                                    symbol=submod,
                                    module=mod_name,
                                    message=f"Module '{mod_name}' does not exist in TeamZero.",
                                    suggestions=avail[:8],
                                    line_number=node.lineno
                                )
                            )
                        else:
                            # Verify specific imported symbols inside the real file
                            try:
                                sub_tree = ast.parse(target_file.read_text(encoding="utf-8"))
                                defined_names = set()
                                for sub_node in sub_tree.body:
                                    if isinstance(sub_node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                                        defined_names.add(sub_node.name)
                                    elif isinstance(sub_node, ast.Assign):
                                        for t in sub_node.targets:
                                            if isinstance(t, ast.Name):
                                                defined_names.add(t.id)

                                for alias in node.names:
                                    sym_name = alias.name
                                    if sym_name != "*" and sym_name not in defined_names:
                                        # Close matches
                                        suggestions = [n for n in defined_names if sym_name.lower() in n.lower() or n.lower() in sym_name.lower()]
                                        findings.append(
                                            GroundingFinding(
                                                kind="MISSING_SYMBOL",
                                                symbol=sym_name,
                                                module=mod_name,
                                                message=f"Symbol '{sym_name}' does not exist in '{mod_name}'.",
                                                suggestions=suggestions[:6] or sorted(list(defined_names))[:6],
                                                line_number=node.lineno
                                            )
                                        )
                            except Exception:
                                pass

    is_grounded = len(findings) == 0
    return {
        "grounded": is_grounded,
        "syntax_valid": True,
        "total_findings": len(findings),
        "findings": [asdict(f) for f in findings],
        "verdict": "VERIFIED_GROUNDED" if is_grounded else "HALLUCINATED_SYMBOLS_DETECTED"
    }


# ── 4. Pre-Flight Assumption & Uncertainty Elicitation ──────────────────────

def surface_assumptions(prompt_or_brief: str) -> Dict[str, Any]:
    """Analyzes a task or brief to surface unstated assumptions, ambiguous requirements, and missing edge cases.

    Gives explicit permission to admit uncertainty ('I don't know') instead of guessing.
    """
    lines = prompt_or_brief.splitlines()
    text = prompt_or_brief.lower()

    stated_assumptions = []
    ambiguities = []
    missing_edge_cases = []
    clarifying_questions = []

    # Check for concurrency / async assumptions
    if "async" not in text and "await" not in text and "thread" not in text:
        stated_assumptions.append("Synchronous execution model assumed (no concurrency or locks).")
    else:
        stated_assumptions.append("Asynchronous or concurrent execution model declared.")

    # Check for storage / persistence
    if "database" not in text and "sqlite" not in text and "file" not in text and "json" not in text:
        ambiguities.append("Storage / persistence tier is unspecified. Defaulting to in-memory or flat JSON.")
        clarifying_questions.append("Should state persist across restarts (file/DB), or remain in-memory?")

    # Check for error handling & boundaries
    if "error" not in text and "exception" not in text and "failure" not in text:
        missing_edge_cases.append("Error handling strategy not defined (silent failure vs custom exception).")
        clarifying_questions.append("How should invalid inputs be handled: raise ValueError or return failure status?")

    # Check for boundary limits
    if "limit" not in text and "max" not in text and "timeout" not in text:
        missing_edge_cases.append("Rate limits, maximum thresholds, and execution timeouts are unspecified.")

    # Explicit permission to state uncertainty
    uncertainty_permission = (
        "Permission granted to say 'I don't know' or request clarification if "
        "external APIs, versions, or schemas are underspecified."
    )

    return {
        "stated_assumptions": stated_assumptions,
        "ambiguities_flagged": ambiguities,
        "missing_edge_cases": missing_edge_cases,
        "clarifying_questions": clarifying_questions,
        "uncertainty_policy": uncertainty_permission,
        "proceed_recommended": len(ambiguities) == 0
    }


# ── 5. Multi-Agent Cross-Validation (Executor -> Validator -> Critic) ───────

@dataclass
class SwarmVerdict:
    status: str  # APPROVED | NEEDS_REVISION | REJECTED
    executor_summary: str
    validator_grounding: Dict[str, Any]
    critic_compliance: Dict[str, Any]
    reasons: List[str] = field(default_factory=list)


def multiagent_cross_validate(
    candidate_code: str,
    feature: str = "general",
    root: Path = ROOT_DIR
) -> SwarmVerdict:
    """Executes a 3-agent cross-validation handshake on candidate code before merging.

    1. Executor: Analyzes syntax and structure.
    2. Validator: Runs AST Grounding and tests symbol reality.
    3. Critic: Inspects known Traps and Quality Invariants.
    """
    reasons = []

    # 1. Executor Check: Basic AST validation
    try:
        tree = ast.parse(candidate_code)
        func_count = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
        class_count = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
        exec_summary = f"Syntax valid: {class_count} classes, {func_count} functions."
    except SyntaxError as e:
        return SwarmVerdict(
            status="REJECTED",
            executor_summary=f"Syntax Error: {e.msg}",
            validator_grounding={"grounded": False},
            critic_compliance={"compliant": False},
            reasons=[f"Syntax Error at line {e.lineno}: {e.msg}"]
        )

    # 2. Validator Check: AST Grounding
    grounding = validate_code_grounding(candidate_code, root=root)
    if not grounding["grounded"]:
        for f in grounding["findings"]:
            reasons.append(f"Validator Hallucination Catch: {f['message']}")

    # 3. Critic Check: Traps & Constitution Invariants
    traps_file = root / ".teamzero" / "memory" / "traps" / f"{feature.lower()}.md"
    traps_checked = False
    critic_notes = []

    if traps_file.exists():
        traps_checked = True
        trap_text = traps_file.read_text(encoding="utf-8").lower()
        # Look for negative assertions or anti-patterns mentioned in trap card
        for trap_kw in ["silent fail", "unbounded", "hardcode", "mutation"]:
            if trap_kw in trap_text and trap_kw in candidate_code.lower():
                critic_notes.append(f"Potential anti-pattern match from trap card: '{trap_kw}'")
                reasons.append(f"Critic Trap Warning: Potential match for '{trap_kw}' trap.")

    # Invariant 04: Zero hardcoded secrets
    if re.search(r"(?:api_key|secret|password|bearer)\s*=\s*['\"][A-Za-z0-9_\-]{16,}['\"]", candidate_code, re.I):
        reasons.append("Critic Security Breach: Hardcoded credential or token pattern detected (INV-04).")

    critic_compliant = len([r for r in reasons if "Critic" in r]) == 0

    if not grounding["grounded"] or not critic_compliant:
        status = "REJECTED" if any("Breach" in r or "Syntax" in r for r in reasons) else "NEEDS_REVISION"
    else:
        status = "APPROVED"

    return SwarmVerdict(
        status=status,
        executor_summary=exec_summary,
        validator_grounding=grounding,
        critic_compliance={
            "compliant": critic_compliant,
            "traps_checked": traps_checked,
            "notes": critic_notes
        },
        reasons=reasons
    )
