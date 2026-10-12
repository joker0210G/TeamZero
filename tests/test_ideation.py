"""Tests for TeamZero Design Thinking Ideation Engine."""

import json
from pathlib import Path
import pytest

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

SAMPLE_MARKDOWN = """# ASK: One-Click Instant Refund
# Stage: Design Thinking Ideation Brief
# Date: 2026-10-12T12:00:00Z
# Author: Alex Founder

## 1. Stage 1: Empathize (Understand the Human Need)
- Target Persona / User: Busy e-commerce customer on mobile
- Observed Friction & Context: Users drop off when refund takes more than 3 form screens
- User Voice / Quote: "Why do I need to re-enter my bank IBAN if you already have my payment card?"
- Underlying Emotional Need: Immediate reassurance and fairness

## 2. Stage 2: Define (Frame the Problem & Boundaries)
- Point of View (POV) Statement: An e-commerce buyer needs instant 1-tap store credit refund because manual bank transfers create churn.
- Core Invariants (Non-Negotiable Business Truths):
  - INV-01: Refund can never exceed original purchase amount
  - INV-02: Banned users cannot claim automatic refunds
- Acceptance Criteria:
  - Refund issued in < 500ms
  - Immediate ledger receipt emitted

## 3. Stage 3: Ideate (Divergent Brainstorming)
- Proposed Hypotheses:
  - Option A: Instant store ledger credit with push notification
  - Option B: Asynchronous Stripe reverse transfer webhook
- Potential Pitfalls & Traps to Watch:
  - Double credit if user double taps button

## 4. Stage 4: Prototype (Minimum Viable Surface)
- Target Module / Service: teamzero.refund_service
- Target Function Signature: calculate_refund
- Scope Boundary: Cross-currency FX conversion is out of scope

## 5. Stage 5: Test (Decision Table & Edge Cases)
| Rule ID | Inputs / Conditions | Expected Outcome |
| :--- | :--- | :--- |
| RULE_01 | days <= 30 and unopened | FULL_REFUND |
| RULE_02 | days > 30 | ZERO_REFUND |
| RULE_03 | is_banned == True | BLOCKED |
"""


def test_parse_ideation_markdown():
    brief = parse_ideation_markdown(SAMPLE_MARKDOWN)
    assert brief.title == "One-Click Instant Refund"
    assert brief.author == "Alex Founder"
    assert brief.empathize.target_persona == "Busy e-commerce customer on mobile"
    assert "Why do I need to re-enter" in brief.empathize.user_quote
    assert len(brief.define.invariants) == 2
    assert "INV-01: Refund can never exceed original purchase amount" in brief.define.invariants
    assert len(brief.ideate.hypotheses) == 2
    assert brief.prototype.target_module == "teamzero.refund_service"
    assert len(brief.test_rules) == 3
    assert brief.test_rules[0].rule_id == "RULE_01"
    assert brief.test_rules[2].expected_outcome == "BLOCKED"


def test_brief_serialization_roundtrip(tmp_path):
    brief = parse_ideation_markdown(SAMPLE_MARKDOWN)
    md_file = save_brief_to_inbox(brief, target_dir=tmp_path)
    assert md_file.exists()

    reparsed = parse_ideation_markdown(md_file.read_text(encoding="utf-8"))
    assert reparsed.title == brief.title
    assert len(reparsed.define.invariants) == len(brief.define.invariants)
    assert len(reparsed.test_rules) == len(brief.test_rules)


def test_compile_brief_to_spec(tmp_path):
    brief = parse_ideation_markdown(SAMPLE_MARKDOWN)
    spec_path = compile_brief_to_spec(brief, specs_dir=tmp_path)
    assert spec_path.exists()

    data = json.loads(spec_path.read_text(encoding="utf-8"))
    assert data["feature"] == "one_click_instant_refund"
    assert data["module"] == "teamzero.refund_service"
    assert len(data["invariants"]) == 2
    assert len(data["decision_table"]) == 3
    assert data["decision_table"][0]["id"] == "RULE_01"
