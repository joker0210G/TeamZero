# ASK: [Feature / Problem Title]
# Stage: Design Thinking Ideation Brief
# Date: YYYY-MM-DD
# Author: Founder

## 1. Stage 1: Empathize (Understand the Human Need)
- Target Persona / User: [Who is struggling? e.g., Solo founder, End user on mobile, DevOps lead]
- Observed Friction & Context: [What observed behavior or friction triggers this ask?]
- User Voice / Quote: "[Verbatim quote or frustration expressed by the user]"
- Underlying Emotional Need: [e.g., Confidence that no secrets leak, relief from tedious manual entry]

## 2. Stage 2: Define (Frame the Problem & Boundaries)
- Point of View (POV) Statement: [User] needs [Action / Capability] because [Core Insight].
- Root Cause Analysis (The 5 Whys):
  - Why 1: [Symptom observed]
  - Why 2: [Direct reason]
  - Why 3: [Underlying operational issue]
  - Why 4: [Systemic gap]
  - Why 5: [Root architectural/business cause]
- How Might We (HMW) Prompt: How might we [Action / Objective] for [User] so that [Outcome]?
- Core Invariants (Non-Negotiable Business Truths):
  - INV-01: [Rule 1, e.g., Refund amount can never exceed total charged amount]
  - INV-02: [Rule 2, e.g., Banned users cannot claim automated vouchers]
- Acceptance Criteria:
  - [Criterion 1]
  - [Criterion 2]

## 3. Stage 3: Ideate (Divergent Brainstorming & Negative Inversion)
- Ideation Technique: [Brainstorming | SCAMPER | Crazy 8s | Reverse Brainstorming]
- Negative / Reverse Brainstorming (How could this fail or frustrate users?):
  - Failure Mode 1: [e.g., Double clicking charges user twice] -> Inverted Solution: [Idempotency key]
  - Failure Mode 2: [e.g., Slow external webhook hangs request] -> Inverted Solution: [Async queue + timeout]
- Proposed Hypotheses:
  - Option A: [Description of approach A]
  - Option B: [Description of approach B - e.g. alternate library or protocol]
- Potential Pitfalls & Traps to Watch:
  - [Trap 1]

## 4. Stage 4: Prototype & Prioritization (MoSCoW & Minimal Surface)
- Prioritization (MoSCoW Matrix):
  - Must Have (M): [Critical core function for v1]
  - Should Have (S): [Important enhancement if budget allows]
  - Could Have (C): [Nice-to-have optimization]
  - Won't Have (W): [Explicitly out of scope for current sprint]
- Impact vs. Effort: [Quick Win (High Impact / Low Effort) | Strategic Build (High/High)]
- Target Module / Service: [e.g., teamzero.billing.refund]
- Target Function Signature: `def process(user_id: str, amount: float) -> dict:`
- Scope Boundary: [What is explicitly OUT of scope for the first iteration?]

## 5. Stage 5: Test (Decision Table & Edge Cases)
| Rule ID | Inputs / Conditions | Expected Outcome |
| :--- | :--- | :--- |
| RULE_01 | condition_a <= 10, valid=True | SUCCESS |
| RULE_02 | condition_a > 10, valid=True | REJECTED |
| RULE_03 | valid=False | ZERO_REFUND |
