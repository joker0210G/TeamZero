"""TeamZero Project Initialization Engine.

Bootstraps the `.teamzero` institutional governance layer inside any target codebase,
allowing TeamZero agents and quality gates to operate on external projects.
"""

from __future__ import annotations
import json
import os
import secrets
import sys
from pathlib import Path
from typing import Optional


STARTER_CONSTITUTION = """# TeamZero Quality Constitution
# Version: 0.1.0.dev1
# The machine-enforced governance layer of TeamZero.
# Invariant: CI and the pipeline enforce this constitution. Agents cannot modify this file.

organization:
  name: "{project_name}"
  mode: "Solo Founder + Autonomous Agents"
  version: "0.1.0.dev1"
  framework_version: "0.1.0.dev1"

invariants:
  - id: INV-01
    name: "Generator Never Verifies"
    rule: "Author agent and reviewer/QA agent must execute on distinct prompts and/or model families."
  - id: INV-02
    name: "QA Sees The Spec, Never The Diff"
    rule: "Acceptance tests are authored strictly against the specification, preventing confirmation bias on implementations."
  - id: INV-03
    name: "Done Is Computed, Never Asserted"
    rule: "Tasks cannot be set to 'done' by any agent or client. Status is computed by the automated pipeline."
  - id: INV-04
    name: "Zero Secrets In Sandbox & Protected Constitution"
    rule: "Execution sandboxes hold no production credentials. Protected paths (.teamzero/constitution*, .github/workflows/*) cannot be modified by agents."
  - id: INV-05
    name: "Failure Has A Price"
    rule: "Failed gates and red-team catches deduct from task token budget and decay agent trust scores."

governance:
  max_repair_attempts: 3
  founder_escalation_on_exhaustion: true
  token_budget_governor:
    max_tokens_per_task: 35000
    redteam_budget_cap_pct: 10
    default_autonomy_level: 2 # Level 0 (suggest only) to Level 5 (ship and notify)
  threat_model_boundary:
    mint_authority: "In bootstrap mode, founder environment holds TZ_SERVER_SECRET. In production/remote mode, CI secret is the exclusive mint authority. Agents never possess or receive TZ_SERVER_SECRET."
    remote_enforcement_trigger: "Remote branch protection becomes non-bypassable condition the moment external agents or MCP clients gain repository write access."

merge_gauntlet:
  deterministic_gates:
    - id: gate_syntax_lint
      name: "Syntax & Lint Verification"
      command: "python -m py_compile {files}"
      blocking: true
    - id: gate_unit_tests
      name: "Automated Test Suite"
      command: "python -m pytest -q tests/"
      blocking: true
    - id: gate_coverage
      name: "Diff Coverage Floor"
      diff_coverage_floor_pct: 100
      total_coverage_floor_pct: 80
      blocking: true
    - id: gate_secret_scan
      name: "Secret & Credential Scan"
      patterns:
        - "(?i)(api[_-]?key|secret|token|password|bearer)\\\\s*[:=]\\\\s*['\\"][A-Za-z0-9_\\\\-]{8,}['\\"]"
        - "(?i)-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
      blocking: true
    - id: gate_dependency_probation
      name: "Zero-Day Dependency Probation"
      max_package_age_days: 7
      blocking: true

redteam_breakers:
  phases:
    - phase: A
      name: "Deterministic Heuristics"
      token_cost: 0
    - phase: B
      name: "Boundary Condition Probing"
      token_cost: 0
    - phase: C
      name: "Semantic Mutation Attacks"
      token_cost: 0
    - phase: D
      name: "LLM Specification Prober"
      budget_tokens: 2500
"""

STARTER_PROVIDERS = """tiers:
  lite:
    provider: "anthropic"
    model: "claude-3-5-haiku-20241022"
    description: "Fast, low-cost tasks: linting, syntax analysis, quick triage"
  standard:
    provider: "anthropic"
    model: "claude-3-5-sonnet-20241022"
    description: "Primary implementation work, code generation, refactoring"
  frontier:
    provider: "anthropic"
    model: "claude-3-opus-20240229"
    description: "High-stakes tasks: architecture design, complex verification, security audit"
"""


def init_project(target_dir: Path, name: Optional[str] = None) -> Path:
    """Initializes the .teamzero governance layer inside target_dir.

    Args:
        target_dir: Path to the target project directory.
        name: Name of the project/organization (defaults to target_dir.name).

    Returns:
        Path to the initialized .teamzero directory.
    """
    target = target_dir.resolve()
    target.mkdir(parents=True, exist_ok=True)
    org_dir = target / ".teamzero"
    org_dir.mkdir(parents=True, exist_ok=True)

    proj_name = name or target.name or "Project"

    # Directory layout
    dirs_to_create = [
        org_dir / "memory" / "specs",
        org_dir / "memory" / "adr",
        org_dir / "memory" / "map",
        org_dir / "memory" / "traps",
        org_dir / "memory" / "evidence",
        org_dir / "memory" / "tasks",
        org_dir / "redteam" / "campaigns",
        org_dir / "redteam" / "findings",
        org_dir / "inbox" / "asks",
        org_dir / "inbox" / "decisions",
        org_dir / "ledger",
        org_dir / "journal",
        org_dir / "triggers",
    ]
    for d in dirs_to_create:
        d.mkdir(parents=True, exist_ok=True)

    # .gitignore inside .teamzero
    tz_gitignore = org_dir / ".gitignore"
    if not tz_gitignore.exists():
        tz_gitignore.write_text(
            "# TeamZero local secrets and caches\n.mintkey\n*.tmp\n__pycache__/\n",
            encoding="utf-8"
        )

    # .mintkey for HMAC receipts
    mintkey_file = org_dir / ".mintkey"
    if not mintkey_file.exists():
        key = secrets.token_hex(32)
        mintkey_file.write_text(key, encoding="utf-8")
        if sys.platform != "win32":
            try:
                os.chmod(mintkey_file, 0o600)
            except Exception:
                pass

    # constitution.yaml
    constitution_file = org_dir / "constitution.yaml"
    if not constitution_file.exists():
        constitution_content = STARTER_CONSTITUTION.replace("{project_name}", proj_name)
        constitution_file.write_text(constitution_content, encoding="utf-8")

    # providers.yaml
    providers_file = org_dir / "providers.yaml"
    if not providers_file.exists():
        providers_file.write_text(STARTER_PROVIDERS, encoding="utf-8")

    # health.json
    health_file = org_dir / "health.json"
    if not health_file.exists():
        initial_health = {
            "overall_status": "HEALTHY",
            "unresolved_critical_count": 0,
            "sla_breaches": [],
            "trust_violations": [],
            "last_check_timestamp": 0
        }
        health_file.write_text(json.dumps(initial_health, indent=2), encoding="utf-8")

    # Initial ledger files
    for ledger_name in ["trust.jsonl", "payroll.jsonl", "receipts.jsonl"]:
        f = org_dir / "ledger" / ledger_name
        if not f.exists():
            f.touch()

    # README in .teamzero
    readme_file = org_dir / "README.md"
    if not readme_file.exists():
        readme_file.write_text(
            f"# TeamZero Governance Layer for {proj_name}\n\n"
            "This directory contains the machine-enforced institutional memory, "
            "executable specifications, architecture decision records (ADRs), "
            "adversarial red-team findings, and cryptographic receipts for this project.\n\n"
            "Managed via the `tz` CLI (`tz status`, `tz gauntlet`, `tz breaker`, `tz inbox`).\n",
            encoding="utf-8"
        )

    return org_dir
