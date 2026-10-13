"""TeamZero Project Bootstrapping Engine.

Initializes the institutional governance layer and project contract for any repository.
Incorporates:
  - TeamZero Project Contract: Non-negotiable boundaries, protected paths, and Zones of Autonomy.
  - Task Tracking: Structured task tracking in memory/tasks/.
  - Architecture Maps: Living architecture maps in memory/map/.
  - Design Thinking: Non-linear 5-round onboarding interview in runbooks/onboarding_session.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import secrets
import shutil
import sys
from pathlib import Path
from typing import Optional

ORG_DIR_NAME = ".teamzero"
TZ_VERSION = "0.2.0-alpha.1"

PROFILES: dict[str, dict] = {
    "python": {
        "detect": ["pyproject.toml", "setup.py", "requirements.txt", "blender_manifest.toml"],
        "gates": [
            {
                "id": "gate_syntax_lint",
                "name": "Syntax & Lint Verification",
                "command": "python -m py_compile $(git diff --name-only --diff-filter=ACMR origin/main...HEAD -- '*.py') 2>/dev/null || python -m compileall -q .",
                "blocking": True,
            },
            {
                "id": "gate_unit_tests",
                "name": "Automated Test Suite",
                "command": "python -m pytest -q tests/",
                "blocking": True,
            },
            {
                "id": "gate_secret_scan",
                "name": "Secret & Credential Scan",
                "patterns": [
                    r"(?i)(api[_-]?key|secret|token|password|bearer)\s*[:=]\s*['\"][A-Za-z0-9_\-]{8,}['\"]",
                    r"(?i)-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
                ],
                "blocking": True,
            },
        ],
    },
    "node": {
        "detect": ["package.json"],
        "gates": [
            {
                "id": "gate_syntax_lint",
                "name": "Lint Verification",
                "command": "npm test --if-present",
                "blocking": True,
            },
            {
                "id": "gate_secret_scan",
                "name": "Secret & Credential Scan",
                "patterns": [
                    r"(?i)(api[_-]?key|secret|token|password|bearer)\s*[:=]\s*['\"][A-Za-z0-9_\-]{8,}['\"]",
                    r"(?i)-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
                ],
                "blocking": True,
            },
        ],
    },
    "generic": {
        "detect": [],
        "gates": [
            {
                "id": "gate_secret_scan",
                "name": "Secret & Credential Scan",
                "patterns": [
                    r"(?i)(api[_-]?key|secret|token|password|bearer)\s*[:=]\s*['\"][A-Za-z0-9_\-]{8,}['\"]",
                    r"(?i)-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
                ],
                "blocking": True,
            },
        ],
    },
}

LEAF_DIRS = [
    "memory/adr",
    "memory/map",
    "memory/specs",
    "memory/tasks",
    "memory/traps",
    "inbox/asks",
    "inbox/decisions",
    "ledger",
    "runbooks",
]

CONSTITUTION_TEMPLATE = """\
# {org_name} Quality Constitution
# Version: {version}
# Initialized on {ts}.
# Invariant: CI and automated referees enforce this constitution. Agents cannot modify this file.

organization:
  name: "{org_name}"
  mode: "Solo Founder + Autonomous AI Co-Workers"
  version: "{version}"
  profile: "{profile}"

# ── Zones of Autonomy ────────────────────────────────────────────────────────
zones_of_autonomy:
  green_autonomy_zone:
    description: "Low-risk, high-frequency actions agents execute autonomously"
    permissions:
      - "Run unit tests and linting"
      - "Read and outline code symbols"
      - "Draft candidate features in sandbox"
      - "Manage task subtasks and dependencies"
  red_supervision_zone:
    description: "High-stakes actions requiring explicit Founder approval via tz inbox"
    requirements:
      - "Merging candidate code to main branch"
      - "Modifying protected architecture or credentials"
      - "Changing project invariants or token budget"

# ── Invariants ────────────────────────────────────────────────────────────────
invariants:
  - id: INV-01
    name: "Generator Never Verifies"
    rule: "Author agent and reviewer/QA agent must execute on distinct prompts and/or model families."
  - id: INV-02
    name: "QA Sees The Spec, Never The Diff"
    rule: "Acceptance tests are authored strictly against the specification, preventing confirmation bias."
  - id: INV-03
    name: "Done Is Computed, Never Asserted"
    rule: "Tasks cannot be set to 'done' by any agent. Status is computed by automated referees."
  - id: INV-04
    name: "Zero Secrets In Sandbox & Protected Constitution"
    rule: "Execution sandboxes hold no production credentials. Protected paths cannot be modified by agents."
  - id: INV-05
    name: "Failure Has A Price"
    rule: "Failed gates deduct from task token budget and decay agent trust scores."

# ── Protected Non-Negotiables (Project Contract) ──────────────────────────────
protected_paths:
  - ".teamzero/constitution.yaml"
  - ".teamzero/PROJECT_CONTRACT.md"
  - ".teamzero/memory/adr/*"
  - ".teamzero/ledger/*"
  - ".github/workflows/*"

merge_gauntlet:
  deterministic_gates:
{gates_yaml}
"""

PROJECT_CONTRACT_TEMPLATE = """\
# 📜 Project Contract: {org_name}
*Established by Founder & TeamZero on {ts}*

> [!NOTE]
> This contract is the human-centered charter for all AI co-workers on this project.
> Agents must respect the Non-Negotiable Boundaries and Zones of Autonomy at all times.

---

## 🎯 1. Mission & Desired Outcomes
- **Project:** {org_name}
- **Profile:** {profile}
- **Founder Goal:** (Synthesized during Design Thinking onboarding interview)

---

## 🛑 2. Non-Negotiable Boundaries (What AI Must NEVER Break)
1. **Never alter core security credentials or secrets.**
2. **Never modify `.teamzero/constitution.yaml` or `.github/workflows/`.**
3. **Never declare tasks 'done' without automated referee test receipts.**
4. **Never overwrite existing user data or baseline simulator environments.**

---

## 🚦 3. Zones of Autonomy
- 🟢 **Green Zone (Autonomous):** Code exploration, running tests, proposing draft PRs, task breakdown.
- 🔴 **Red Zone (Supervised):** Merging code, deploying to users, deleting files, spending budget.

---

## 📬 4. Founder Communication
When high-stakes decisions arise, agents file an Executive Ask in `.teamzero/inbox/asks/`.
The Founder reviews and steers via:
```bash
tz inbox
```
"""

ONBOARDING_RUNBOOK_TEMPLATE = """\
# 🧠 AI Co-Worker Runbook: Design Thinking Onboarding Interview
*Instructions for Claude Code / Antigravity / Cursor when initializing a new project with TeamZero*

When a Founder starts a new project, conduct a non-linear Design Thinking interview:

### 1. Empathize & Discover
- Ask the Founder: What is your vision? Who is the end user? What frustration does this solve?
- Listen deeply. Do not demand technical code specs upfront.

### 2. Define the Challenge
- Synthesize into a clear problem statement: "How might we [goal] for [user] without [friction]?"

### 3. Ideate & Tech Scouting
- Scout modern open-source tools and patterns (referencing TaskMaster for tasks, Graphify for maps).
- Balance Desirability, Feasibility, Viability, and Responsibility.

### 4. Prototype the Contract
- Fill out `.teamzero/PROJECT_CONTRACT.md` and seed initial tasks in `.teamzero/memory/tasks/`.

### 5. Test & Launch
- Present the 1-page summary to the Founder. Once approved, launch the autonomous worker agents!
"""

ADR_GENESIS_TEMPLATE = """\
# ADR-000: TeamZero Genesis — Governance Layer Initialization

- Status: Accepted
- Date: {ts}
- Decided by: founder (via `teamzero init`)

## Context
The project adopted the TeamZero institutional operating system. This ADR proves when
and into which project the governance layer was initialized, anchoring the root of trust.

## Decision
- Constitution v{version} is in force for `{org_name}` (profile: `{profile}`).
- Local mint key at `.teamzero/.mintkey` is the bootstrap mint authority.
- Deterministic gates: {gate_ids}
"""

MCP_SERVER_BLOCK = {
    "mcpServers": {
        "teamzero": {
            "command": sys.executable,
            "args": ["-m", "teamzero.mcp_server"],
            "env": {
                "PYTHONIOENCODING": "utf-8"
            },
        }
    }
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def detect_profile(root: Path, forced: str) -> str:
    if forced and forced != "auto":
        return forced if forced in PROFILES else "generic"
    for name, p in PROFILES.items():
        if any((root / marker).exists() for marker in p.get("detect", [])):
            return name
    return "generic"


def gates_to_yaml(gates: list[dict]) -> str:
    lines = []
    for g in gates:
        lines.append(f"    - id: \"{g['id']}\"")
        lines.append(f"      name: \"{g['name']}\"")
        if "command" in g:
            lines.append(f"      command: \"{g['command']}\"")
        lines.append(f"      blocking: {str(g.get('blocking', True)).lower()}")
    return "\n".join(lines)


def mint_genesis_receipt(org_dir: Path, project_name: str, profile: str) -> dict:
    mintkey_path = org_dir / ".mintkey"
    if not mintkey_path.exists():
        key = secrets.token_bytes(32)
        mintkey_path.write_bytes(key)
    else:
        key = mintkey_path.read_bytes()

    payload = {
        "event": "genesis",
        "org": project_name,
        "profile": profile,
        "version": TZ_VERSION,
        "ts": utc_now(),
    }
    canonical = json.dumps(payload, sort_keys=True).encode("utf-8")
    sig = hmac.new(key, canonical, hashlib.sha256).hexdigest()
    return {**payload, "receipt_hmac": sig}


def merge_gitignore(root: Path) -> list[str]:
    gi = root / ".gitignore"
    entry = ".teamzero/.mintkey"
    if gi.exists():
        text = gi.read_text(encoding="utf-8")
        if entry not in text:
            gi.write_text(text.rstrip() + f"\n{entry}\n", encoding="utf-8")
            return [f"added {entry} to .gitignore"]
        return []
    gi.write_text(f"{entry}\n", encoding="utf-8")
    return [f"created .gitignore with {entry}"]


def write_mcp_configs(root: Path) -> list[str]:
    actions = []
    configs = [
        root / ".mcp.json",
        root / "claude_mcp.json",
        root / "antigravity_mcp.json",
    ]
    block_json = json.dumps(MCP_SERVER_BLOCK, indent=2)
    for cfg in configs:
        if not cfg.exists():
            cfg.write_text(block_json, encoding="utf-8")
            actions.append(f"wrote {cfg.name}")
    return actions


def init_project(target_dir: Path, name: Optional[str] = None, force: bool = False) -> Path:
    root = target_dir.resolve()
    org_dir = root / ORG_DIR_NAME

    if org_dir.exists():
        if not force:
            raise FileExistsError(f"{org_dir} already exists. Use force=True to re-initialize.")
        backup = root / f"{ORG_DIR_NAME}.backup.{dt.datetime.now().strftime('%Y%m%d%H%M%S')}"
        shutil.move(str(org_dir), str(backup))

    profile = detect_profile(root, "auto")
    project_name = name or root.name
    ts = utc_now()
    gates = PROFILES[profile]["gates"]

    for leaf in LEAF_DIRS:
        (org_dir / leaf).mkdir(parents=True, exist_ok=True)

    # 1. Constitution with Autonomy Zones
    const_text = CONSTITUTION_TEMPLATE.format(
        org_name=project_name,
        version=TZ_VERSION,
        ts=ts,
        profile=profile,
        gates_yaml=gates_to_yaml(gates),
    )
    (org_dir / "constitution.yaml").write_text(const_text, encoding="utf-8")

    # 2. Project Contract (Founder Charter)
    contract_text = PROJECT_CONTRACT_TEMPLATE.format(
        org_name=project_name,
        version=TZ_VERSION,
        ts=ts,
        profile=profile,
    )
    (org_dir / "PROJECT_CONTRACT.md").write_text(contract_text, encoding="utf-8")

    # 3. Genesis ADR
    adr_text = ADR_GENESIS_TEMPLATE.format(
        ts=ts,
        version=TZ_VERSION,
        org_name=project_name,
        profile=profile,
        gate_ids=", ".join(g["id"] for g in gates),
    )
    (org_dir / "memory" / "adr" / "ADR-000-genesis.md").write_text(adr_text, encoding="utf-8")

    # 4. Onboarding Design Thinking Runbook
    (org_dir / "runbooks" / "onboarding_session.md").write_text(ONBOARDING_RUNBOOK_TEMPLATE, encoding="utf-8")

    # 5. Genesis Receipt & Trust Ledger
    receipt = mint_genesis_receipt(org_dir, project_name, profile)
    with (org_dir / "ledger" / "receipts.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(receipt) + "\n")
    with (org_dir / "ledger" / "trust.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": ts, "agent": "founder", "event": "genesis", "trust": 1.0}) + "\n")

    merge_gitignore(root)
    write_mcp_configs(root)

    return org_dir


def cmd_doctor(args) -> int:
    target_path = getattr(args, "project_root", None) or getattr(args, "path", ".")
    root = Path(target_path).resolve()
    org_dir = root / ORG_DIR_NAME

    if not org_dir.is_dir():
        print(f"error: {org_dir} not found. Run 'teamzero init' first.", file=sys.stderr)
        return 1

    ok = True
    for req in ["constitution.yaml", "PROJECT_CONTRACT.md", ".mintkey", "memory/adr/ADR-000-genesis.md"]:
        if not (org_dir / req).exists():
            print(f"[FAIL] Missing {req}", file=sys.stderr)
            ok = False
        else:
            print(f"[OK] Found {req}")

    return 0 if ok else 1
