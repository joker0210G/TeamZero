"""Design Thinking Ideation Engine for TeamZero.

Bridges human-centered problem solving with automated agent execution:
1. Empathize: Capture user persona, direct friction, and emotional pain points.
2. Define: Formulate actionable POV problem statements and hard business invariants.
3. Ideate: Frame competing architectural hypotheses for `tz race`.
4. Prototype: Define minimal viable surface (module, functions, contracts).
5. Test: Convert decision matrices into executable specs for `tz spec`.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from teamzero.config import ASKS_DIR, SPECS_DIR


@dataclass
class EmpathizePhase:
    target_persona: str = ""
    observed_friction: str = ""
    user_quote: str = ""
    emotional_need: str = ""


@dataclass
class DefinePhase:
    pov_statement: str = ""
    invariants: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)


@dataclass
class IdeatePhase:
    hypotheses: List[Dict[str, str]] = field(default_factory=list)
    pitfalls_to_watch: List[str] = field(default_factory=list)


@dataclass
class PrototypePhase:
    target_module: str = ""
    target_function: str = ""
    scope_boundary: str = ""


@dataclass
class IdeationTestRule:
    rule_id: str
    condition: str
    expected_outcome: str


@dataclass
class DesignThinkingBrief:
    title: str
    author: str = "Founder"
    created_at: str = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
    empathize: EmpathizePhase = field(default_factory=EmpathizePhase)
    define: DefinePhase = field(default_factory=DefinePhase)
    ideate: IdeatePhase = field(default_factory=IdeatePhase)
    prototype: PrototypePhase = field(default_factory=PrototypePhase)
    test_rules: List[IdeationTestRule] = field(default_factory=list)

    def to_markdown(self) -> str:
        inv_lines = "\n".join(f"  - {inv}" for inv in self.define.invariants) if self.define.invariants else "  - None specified"
        ac_lines = "\n".join(f"  - {ac}" for ac in self.define.acceptance_criteria) if self.define.acceptance_criteria else "  - None specified"
        hypo_lines = "\n".join(f"  - Option {h.get('name', 'N/A')}: {h.get('desc', '')}" for h in self.ideate.hypotheses) if self.ideate.hypotheses else "  - None specified"
        pitfall_lines = "\n".join(f"  - {p}" for p in self.ideate.pitfalls_to_watch) if self.ideate.pitfalls_to_watch else "  - None specified"

        table_rows = []
        for r in self.test_rules:
            table_rows.append(f"| {r.rule_id} | {r.condition} | {r.expected_outcome} |")
        table_content = "\n".join(table_rows) if table_rows else "| RULE_01 | default condition | SUCCESS |"

        return f"""# ASK: {self.title}
# Stage: Design Thinking Ideation Brief
# Date: {self.created_at}
# Author: {self.author}

## 1. Stage 1: Empathize (Understand the Human Need)
- Target Persona / User: {self.empathize.target_persona}
- Observed Friction & Context: {self.empathize.observed_friction}
- User Voice / Quote: "{self.empathize.user_quote}"
- Underlying Emotional Need: {self.empathize.emotional_need}

## 2. Stage 2: Define (Frame the Problem & Boundaries)
- Point of View (POV) Statement: {self.define.pov_statement}
- Core Invariants (Non-Negotiable Business Truths):
{inv_lines}
- Acceptance Criteria:
{ac_lines}

## 3. Stage 3: Ideate (Divergent Brainstorming)
- Proposed Hypotheses:
{hypo_lines}
- Potential Pitfalls & Traps to Watch:
{pitfall_lines}

## 4. Stage 4: Prototype (Minimum Viable Surface)
- Target Module / Service: {self.prototype.target_module}
- Target Function Signature: {self.prototype.target_function}
- Scope Boundary: {self.prototype.scope_boundary}

## 5. Stage 5: Test (Decision Table & Edge Cases)
| Rule ID | Inputs / Conditions | Expected Outcome |
| :--- | :--- | :--- |
{table_content}
"""

    def to_spec_dict(self) -> Dict[str, Any]:
        """Converts brief into TeamZero spec_compiler JSON format."""
        slug = re.sub(r"[^a-zA-Z0-9_]+", "_", self.title.lower()).strip("_")
        
        decision_table = []
        for tr in self.test_rules:
            decision_table.append({
                "id": tr.rule_id,
                "description": f"Enforce {tr.condition}",
                "when": {"condition": tr.condition},
                "then": {"outcome": tr.expected_outcome}
            })

        return {
            "feature": slug,
            "title": self.title,
            "module": self.prototype.target_module or f"teamzero.{slug}",
            "function": self.prototype.target_function or "run_feature",
            "invariants": self.define.invariants,
            "hypotheses": [h.get("name", "") for h in self.ideate.hypotheses],
            "decision_table": decision_table,
            "metadata": {
                "author": self.author,
                "created_at": self.created_at,
                "persona": self.empathize.target_persona,
                "pov": self.define.pov_statement
            }
        }


def parse_ideation_markdown(content: str) -> DesignThinkingBrief:
    """Parses a Design Thinking markdown document into a structured brief."""
    title_match = re.search(r"^#\s+ASK:\s*(.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "Untitled Ideation"

    author_match = re.search(r"^#\s+Author:\s*(.+)$", content, re.MULTILINE)
    author = author_match.group(1).strip() if author_match else "Founder"

    # Empathize
    persona_m = re.search(r"- Target Persona / User:\s*(.+)", content)
    friction_m = re.search(r"- Observed Friction & Context:\s*(.+)", content)
    quote_m = re.search(r"- User Voice / Quote:\s*\"?([^\"]+)\"?", content)
    need_m = re.search(r"- Underlying Emotional Need:\s*(.+)", content)

    empathize = EmpathizePhase(
        target_persona=persona_m.group(1).strip() if persona_m else "",
        observed_friction=friction_m.group(1).strip() if friction_m else "",
        user_quote=quote_m.group(1).strip() if quote_m else "",
        emotional_need=need_m.group(1).strip() if need_m else "",
    )

    # Define
    pov_m = re.search(r"- Point of View \(POV\) Statement:\s*(.+)", content)
    invariants = []
    inv_section = re.search(r"- Core Invariants.*?:(.*?)(?:- Acceptance Criteria|\n## )", content, re.DOTALL)
    if inv_section:
        for line in inv_section.group(1).splitlines():
            line = line.strip()
            if line.startswith("- "):
                invariants.append(line[2:].strip())

    ac = []
    ac_section = re.search(r"- Acceptance Criteria.*?:(.*?)(?:\n## |\Z)", content, re.DOTALL)
    if ac_section:
        for line in ac_section.group(1).splitlines():
            line = line.strip()
            if line.startswith("- "):
                ac.append(line[2:].strip())

    define = DefinePhase(
        pov_statement=pov_m.group(1).strip() if pov_m else "",
        invariants=invariants,
        acceptance_criteria=ac,
    )

    # Ideate
    hypotheses = []
    hypo_section = re.search(r"- Proposed Hypotheses.*?:(.*?)(?:- Potential Pitfalls|\n## )", content, re.DOTALL)
    if hypo_section:
        for line in hypo_section.group(1).splitlines():
            line = line.strip()
            if line.startswith("- "):
                parts = line[2:].split(":", 1)
                name = parts[0].replace("Option", "").strip()
                desc = parts[1].strip() if len(parts) > 1 else ""
                hypotheses.append({"name": name, "desc": desc})

    pitfalls = []
    pit_section = re.search(r"- Potential Pitfalls.*?:(.*?)(?:\n## |\Z)", content, re.DOTALL)
    if pit_section:
        for line in pit_section.group(1).splitlines():
            line = line.strip()
            if line.startswith("- "):
                pitfalls.append(line[2:].strip())

    ideate = IdeatePhase(hypotheses=hypotheses, pitfalls_to_watch=pitfalls)

    # Prototype
    mod_m = re.search(r"- Target Module / Service:\s*(.+)", content)
    fn_m = re.search(r"- Target Function Signature:\s*(.+)", content)
    scope_m = re.search(r"- Scope Boundary:\s*(.+)", content)

    prototype = PrototypePhase(
        target_module=mod_m.group(1).strip() if mod_m else "",
        target_function=fn_m.group(1).strip() if fn_m else "",
        scope_boundary=scope_m.group(1).strip() if scope_m else "",
    )

    # Test Rules
    test_rules = []
    table_m = re.findall(r"\|\s*([A-Za-z0-9_-]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|", content)
    for rid, cond, out in table_m:
        if rid.lower() in ("rule id", ":---", "---"):
            continue
        test_rules.append(IdeationTestRule(rule_id=rid.strip(), condition=cond.strip(), expected_outcome=out.strip()))

    return DesignThinkingBrief(
        title=title,
        author=author,
        empathize=empathize,
        define=define,
        ideate=ideate,
        prototype=prototype,
        test_rules=test_rules,
    )


def save_brief_to_inbox(brief: DesignThinkingBrief, target_dir: Optional[Path] = None) -> Path:
    """Saves brief markdown to .teamzero/inbox/asks/ and returns Path."""
    out_dir = target_dir or ASKS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", brief.title.lower()).strip("_")
    filename = f"ASK_{slug}.md"
    file_path = out_dir / filename
    file_path.write_text(brief.to_markdown(), encoding="utf-8")
    return file_path


def compile_brief_to_spec(brief: DesignThinkingBrief, specs_dir: Optional[Path] = None) -> Path:
    """Compiles a brief into a spec JSON ready for spec_compiler.py."""
    s_dir = specs_dir or SPECS_DIR
    s_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", brief.title.lower()).strip("_")
    spec_path = s_dir / f"{slug}.json"
    spec_dict = brief.to_spec_dict()
    spec_path.write_text(json.dumps(spec_dict, indent=2), encoding="utf-8")
    return spec_path
