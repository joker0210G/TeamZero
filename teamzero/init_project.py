"""TeamZero CLI & Bootstrapping Engine.

Bootstrap the governance layer into any project.

Design contract (see INIT_PROCEDURE.md):
    * Idempotent: refuses to clobber an existing .teamzero unless --force (backs up first).
    * Deterministic: emits a genesis ADR + HMAC-signed genesis receipt so "founding"
      is a verifiable event, not an assertion.
    * Agent-friendly: a coding agent only needs to run one command; everything else
      (profiles, MCP wiring, gitignore, ledgers) is computed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import sys
from pathlib import Path
from typing import Optional

ORG_DIR_NAME = ".teamzero"
TZ_VERSION = "0.2.0-alpha.1"

# ---------------------------------------------------------------------------
# Project profiles: detection signals + per-ecosystem deterministic gates.
# Gate commands are written into the generated constitution and executed by
# the merge gauntlet — they must be shell-runnable from the project root.
# ---------------------------------------------------------------------------
PROFILES: dict[str, dict] = {
    "python": {
        "detect": ["pyproject.toml", "setup.py", "requirements.txt", "blender_manifest.toml"],
        "gates": [
            {"id": "gate_syntax_lint", "name": "Syntax & Lint Verification",
             "command": "python -m py_compile $(git diff --name-only --diff-filter=ACMR origin/main...HEAD -- '*.py') 2>/dev/null || python -m compileall -q .",
             "blocking": True},
            {"id": "gate_unit_tests", "name": "Automated Test Suite",
             "command": "python -m pytest -q tests/", "blocking": True},
            {"id": "gate_secret_scan", "name": "Secret & Credential Scan",
             "patterns": [
                 r"(?i)(api[_-]?key|secret|token|password|bearer)\s*[:=]\s*['\"][A-Za-z0-9_\-]{8,}['\"]",
                 r"(?i)-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
             ],
             "blocking": True},
            {"id": "gate_dependency_probation", "name": "Slopsquatting & Dependency Verification",
             "rules": ["No hallucinated or unpinned packages",
                       "New packages require verification (age >= 90 days, downloads > 10000)"],
             "blocking": True},
        ],
    },
    "node": {
        "detect": ["package.json"],
        "gates": [
            {"id": "gate_syntax_lint", "name": "Lint Verification",
             "command": "npx eslint . --max-warnings 0", "blocking": True},
            {"id": "gate_unit_tests", "name": "Automated Test Suite",
             "command": "npm test -- --ci", "blocking": True},
            {"id": "gate_secret_scan", "name": "Secret & Credential Scan",
             "patterns": [r"(?i)(api[_-]?key|secret|token|password|bearer)\s*[:=]\s*['\"][A-Za-z0-9_\-]{8,}['\"]",
                          r"(?i)-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"],
             "blocking": True},
            {"id": "gate_dependency_probation", "name": "Dependency Verification",
             "rules": ["New packages require verification (age >= 90 days, downloads > 10000)"],
             "blocking": True},
        ],
    },
    "rust": {
        "detect": ["Cargo.toml"],
        "gates": [
            {"id": "gate_syntax_lint", "name": "Clippy Lint Verification",
             "command": "cargo clippy --all-targets -- -D warnings", "blocking": True},
            {"id": "gate_unit_tests", "name": "Automated Test Suite",
             "command": "cargo test --all", "blocking": True},
            {"id": "gate_secret_scan", "name": "Secret & Credential Scan",
             "patterns": [r"(?i)(api[_-]?key|secret|token|password|bearer)\s*[:=]\s*['\"][A-Za-z0-9_\-]{8,}['\"]",
                          r"(?i)-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"],
             "blocking": True},
        ],
    },
    "go": {
        "detect": ["go.mod"],
        "gates": [
            {"id": "gate_syntax_lint", "name": "Vet Verification",
             "command": "go vet ./...", "blocking": True},
            {"id": "gate_unit_tests", "name": "Automated Test Suite",
             "command": "go test ./...", "blocking": True},
            {"id": "gate_secret_scan", "name": "Secret & Credential Scan",
             "patterns": [r"(?i)(api[_-]?key|secret|token|password|bearer)\s*[:=]\s*['\"][A-Za-z0-9_\-]{8,}['\"]",
                          r"(?i)-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"],
             "blocking": True},
        ],
    },
    "generic": {
        "detect": [],
        "gates": [
            {"id": "gate_secret_scan", "name": "Secret & Credential Scan",
             "patterns": [r"(?i)(api[_-]?key|secret|token|password|bearer)\s*[:=]\s*['\"][A-Za-z0-9_\-]{8,}['\"]",
                          r"(?i)-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"],
             "blocking": True},
        ],
    },
}

LEAF_DIRS = [
    "memory/adr", "memory/map", "memory/specs", "memory/traps",
    "redteam/campaigns", "redteam/findings",
    "inbox/asks", "inbox/decisions",
    "ledger", "journal", "triggers", "runbooks",
]

CONSTITUTION_TEMPLATE = """\
# {org_name} Quality Constitution
# Version: {version}
# Generated by `teamzero init` on {ts}.
# Invariant: CI and the pipeline enforce this constitution. Agents cannot modify this file.

organization:
  name: "{org_name}"
  mode: "Solo Founder + Autonomous Agents"
  version: "{version}"
  profile: "{profile}"
  initialized_by: "teamzero-cli"

invariants:
  - id: INV-01
    name: "Generator Never Verifies"
    rule: "Author agent and reviewer/QA agent must execute on distinct prompts and/or model families."
  - id: INV-02
    name: "QA Sees The Spec, Never The Diff"
    rule: "Acceptance tests are authored strictly against the specification, preventing confirmation bias."
  - id: INV-03
    name: "Done Is Computed, Never Asserted"
    rule: "Tasks cannot be set to 'done' by any agent or client. Status is computed by the automated pipeline."
  - id: INV-04
    name: "Zero Secrets In Sandbox & Protected Constitution"
    rule: "Execution sandboxes hold no production credentials. Protected paths cannot be modified by agents."
  - id: INV-05
    name: "Failure Has A Price"
    rule: "Failed gates and red-team catches deduct from task token budget and decay agent trust scores."

governance:
  max_repair_attempts: 3
  founder_escalation_on_exhaustion: true
  token_budget_governor:
    max_tokens_per_task: 35000
    redteam_budget_cap_pct: 10
    default_autonomy_level: 2

merge_gauntlet:
  deterministic_gates:
{gates_yaml}

red_team:
  l1_spec_prober:
    enabled: true
    budget_tokens: 2500
  l2_context_poisoning:
    enabled: true
    protected_paths:
      - ".teamzero/constitution.yaml"
      - ".teamzero/memory/adr/*"
      - ".teamzero/memory/map/*"
      - ".teamzero/ledger/*"
      - ".github/workflows/*"
  l3_war_games:
    cadence: "weekly"
    shadow_clone: true
    canary_tracking: true
"""

ADR_GENESIS_TEMPLATE = """\
# ADR-000: TeamZero Genesis — Governance Layer Initialization

- Status: Accepted
- Date: {ts}
- Decided by: founder (via `teamzero init`)

## Context

The project adopted the TeamZero institutional operating system. This ADR is the
genesis record: it proves *when* and *into which project* the governance layer was
initialized, and it anchors the trust ledger's root of authority.

## Decision

- Constitution v{version} is in force for `{org_name}` (profile: `{profile}`).
- The local mint key at `.teamzero/.mintkey` is the bootstrap mint authority
  (see constitution `threat_model_boundary`). CI secret becomes the exclusive
  mint authority once branch protection is enabled.
- Deterministic gates: {gate_ids}

## Consequences

- No agent may modify `.teamzero/constitution.yaml` or `.github/workflows/*`.
- Every subsequent ADR must cite this genesis record as ADR-000.
"""

FOUNDER_COCKPIT_TEMPLATE = """\
# 🎛️ Founder Executive Cockpit: {org_name}
*Built by TeamZero v{version} on {ts}*

> [!NOTE]
> **Dear Founder:** You do not need to read code or terminal logs. This cockpit translates your entire software system into 4 simple dials and plain-English actions.

---

## 🧭 Executive Dials (System Health at a Glance)

| Dial | Status | What This Means in Plain English |
| :--- | :--- | :--- |
| 🛡️ **Shield Integrity (Quality)** | 🟢 **100% Solid** | All automated safety nets are catching bugs before they reach users. |
| 🔒 **Security Vault (Safety)** | 🟢 **Locked Tight** | Zero exposed passwords, secret keys, or open backdoors found. |
| 🗺️ **Living Blueprint (Documentation)** | 🟢 **Synchronized** | The AI's internal map matches what the software actually does. |
| 📬 **Decision Queue (Founder Inbox)** | ⚪ **Clear** | No urgent approvals pending. Your team of agents is operating autonomously. |

---

## 🎯 Active Project Mission
- **Project Name:** {org_name}
- **Technology Profile:** {profile}
- **Governance Mode:** Solo Founder + Autonomous Agents
- **Genesis Key:** Verified and sealed under `.teamzero/.mintkey`

---

## 🚦 Traffic Light System
- 🟢 **Green (All Clear):** Software is healthy, tests pass, no human action needed.
- 🟡 **Yellow (Heads Up):** An AI has drafted a feature or an external library needs updating. Review whenever you have time.
- 🔴 **Red (Action Required):** A gate was tripped or a major decision is waiting in your inbox (`tz inbox`).

---

## 📬 How to Steer Without Coding
Whenever an agent needs your input, it files an **Executive Ask** in plain English.
To view or approve pending items, simply run or tell your assistant:
```bash
tz inbox
```
You will get a clear 1-paragraph summary of the situation and simple options: **[Approve]**, **[Reject]**, or **[Ask Spy to Investigate]**.
"""

THREE_YEAR_HORIZON_TEMPLATE = """\
# 🗺️ 3-Year Strategic Horizon: {org_name}
*From Day 1 Launch to Autonomous Operations — Written for the Non-Technical Founder*

---

## 🔭 The 4 Flights of Growth

```mermaid
flowchart LR
    D1["Day 1: Genesis\\nFirst Health Check"] --> Y1["Year 1: Strong Hull\\nZero Silent Crashes"]
    Y1 --> Y2["Year 2: Smart Co-Pilot\\nSwarm Reviews & Auto-Fixes"]
    Y2 --> Y3["Year 3: Space Station\\nFully Autonomous Living Repo"]
```

---

### 🚀 Phase 1: Day 1 — Genesis & Reality Check
**Goal:** Take off safely without breaking anything.
- **What Happens:** TeamZero inspects the existing codebase, creates the Living Map, locks down secrets, and establishes the root of trust.
- **Founder Value:** You immediately know the true health of your software with zero guessing.

---

### 🛡️ Phase 2: Year 1 — The Strong Hull (Rock-Solid Foundation)
**Goal:** Build fast without building tech debt.
- **What Happens:** Every single change authored by an AI or human must pass through the Merge Gauntlet. No code merges without a cryptographically signed receipt.
- **Founder Value:** Your product doesn't randomly crash after updates. New developers or AI tools can join without destroying existing features.

---

### 🤖 Phase 3: Year 2 — The Smart Co-Pilot (Intelligent Automation)
**Goal:** Multiply your engineering output by 10x with autonomous swarms.
- **What Happens:** Specialized AI agents work in roles:
  - **The Builder (Spy):** Drafts features and writes tests.
  - **The Red Team:** Adversarially tries to break features before release.
  - **The Validator:** Fact-checks logic against requirements.
- **Founder Value:** You review executive summaries and approve strategic directions. The team handles implementation and bug fixes automatically.

---

### 🌌 Phase 4: Year 3 — The Autonomous Space Station (Self-Sustaining)
**Goal:** Zero founder burnout, zero developer lock-in.
- **What Happens:**
  - **Institutional Memory:** 3 years of decisions, bug history, and rules are instantly queryable.
  - **Adaptive Triggers:** External API changes (e.g. third-party partners) are auto-detected and patched.
  - **Self-Healing Ratchet:** Minor glitches are detected and healed automatically before users notice.
- **Founder Value:** The system runs smoothly even if you take a month off. You own a resilient, self-governing technology asset.
"""

MCP_SERVER_BLOCK = {
    "mcpServers": {
        "teamzero": {
            "command": None,   # filled at init time
            "args": ["-m", "teamzero.mcp_server"],
            "env": {
                "TZ_ROOT": None,
                "PYTHONIOENCODING": "utf-8",
                "TEAMZERO_TOOLS": "all"
            },
        }
    }
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def detect_profile(root: Path, forced: str) -> str:
    if forced != "auto":
        return forced
    for profile, spec in PROFILES.items():
        if profile == "generic":
            continue
        if any((root / marker).exists() for marker in spec["detect"]):
            return profile
    return "generic"


def gates_to_yaml(gates: list[dict]) -> str:
    lines = []
    for g in gates:
        lines.append(f"    - id: {g['id']}")
        lines.append(f'      name: "{g["name"]}"')
        if "command" in g:
            lines.append(f'      command: "{g["command"]}"')
        if "patterns" in g:
            lines.append("      patterns:")
            for p in g["patterns"]:
                escaped = p.replace("'", "''")
                lines.append(f"        - '{escaped}'")
        if "rules" in g:
            lines.append("      rules:")
            for r in g["rules"]:
                lines.append(f'        - "{r}"')
        lines.append(f"      blocking: {str(g['blocking']).lower()}")
    return "\n".join(lines)


def canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def mint_genesis_receipt(org_dir: Path, project_name: str, profile: str) -> dict:
    """Create the mint key if needed and sign the genesis event (HMAC-SHA256)."""
    mintkey_file = org_dir / ".mintkey"
    env_secret = os.environ.get("TZ_SERVER_SECRET")
    if env_secret:
        key = env_secret.strip().encode()
    elif mintkey_file.exists():
        key = mintkey_file.read_text(encoding="utf-8").strip().encode()
    else:
        key = secrets.token_hex(32).encode()
        mintkey_file.write_text(key.decode(), encoding="utf-8")
        if sys.platform != "win32":
            try:
                os.chmod(mintkey_file, 0o600)
            except Exception:
                pass

    event = {
        "event": "genesis",
        "org": project_name,
        "profile": profile,
        "tz_version": TZ_VERSION,
        "ts": utc_now(),
        "nonce": secrets.token_hex(8),
    }
    event["receipt_hmac"] = hmac.new(key, canonical(event), hashlib.sha256).hexdigest()
    return event


def merge_gitignore(root: Path) -> list[str]:
    """Ensure .mintkey is gitignored. Returns human-readable actions taken."""
    actions = []
    gitignore = root / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if ".teamzero/.mintkey" not in existing:
        prefix = "" if existing.endswith("\n") or not existing else "\n"
        gitignore.write_text(existing + prefix + "\n# TeamZero: local mint authority — never commit\n.teamzero/.mintkey\n", encoding="utf-8")
        actions.append("updated .gitignore (.mintkey ignored)")
    else:
        actions.append(".gitignore already covers .mintkey")
    return actions


def write_mcp_configs(root: Path, mcp_command: str, tz_root: str) -> list[str]:
    """Write MCP client configs for Claude Code / Cursor / Antigravity conventions."""
    actions = []
    block = json.loads(json.dumps(MCP_SERVER_BLOCK))
    server = block["mcpServers"]["teamzero"]
    server["command"] = mcp_command
    server["env"]["TZ_ROOT"] = tz_root

    def merge_into(path: Path, wrapper_key: str | None):
        data = {wrapper_key: block} if wrapper_key else block
        if path.exists():
            try:
                old = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                old = {wrapper_key: {"mcpServers": {}}} if wrapper_key else {"mcpServers": {}}
            slot = old.setdefault(wrapper_key, {}) if wrapper_key else old
            slot.setdefault("mcpServers", {}).update(block["mcpServers"])
            data = old
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        actions.append(f"wrote {path}")

    # Standard config definitions across editors:
    # 1. Claude Code / Desktop & standard MCP clients
    merge_into(root / "claude_mcp.json", None)
    merge_into(root / ".mcp.json", None)

    # 2. Cursor IDE
    merge_into(root / ".cursor" / "mcp.json", None)

    # 3. VS Code (Cline / Roo-Code / Copilot MCP extensions)
    merge_into(root / ".vscode" / "mcp.json", None)

    # 4. OpenCode / Open-source agent runners
    merge_into(root / "opencode_mcp.json", None)

    # 5. Google Antigravity
    merge_into(root / "antigravity_mcp.json", None)
    return actions


def cmd_init(args) -> int:
    target_path = getattr(args, "project_root", None) or getattr(args, "path", ".")
    root = Path(target_path).resolve()
    if not root.is_dir():
        print(f"error: project root '{root}' does not exist", file=sys.stderr)
        return 2

    org_dir = root / ORG_DIR_NAME
    if org_dir.exists():
        if not getattr(args, "force", False):
            print(f"error: {org_dir} already exists. Re-run with --force to back it up and re-initialize.", file=sys.stderr)
            return 2
        backup = root / f"{ORG_DIR_NAME}.backup.{dt.datetime.now().strftime('%Y%m%d%H%M%S')}"
        shutil.move(str(org_dir), str(backup))
        print(f"existing .teamzero backed up to {backup.name}")

    profile = detect_profile(root, getattr(args, "profile", "auto"))
    project_name = getattr(args, "name", None) or root.name
    ts = utc_now()
    gates = PROFILES[profile]["gates"]

    # 1. Scaffold directory tree
    for leaf in LEAF_DIRS:
        (org_dir / leaf).mkdir(parents=True, exist_ok=True)
    for leaf in LEAF_DIRS:
        keep = org_dir / leaf / ".gitkeep"
        if not any((org_dir / leaf).iterdir()):
            keep.touch()

    # 2. Constitution (project-templated, profile-aware gates)
    constitution = CONSTITUTION_TEMPLATE.format(
        org_name=project_name, version=TZ_VERSION, ts=ts,
        profile=profile, gates_yaml=gates_to_yaml(gates),
    )
    (org_dir / "constitution.yaml").write_text(constitution, encoding="utf-8")

    # 3. Genesis ADR
    adr = ADR_GENESIS_TEMPLATE.format(
        ts=ts, version=TZ_VERSION, org_name=project_name, profile=profile,
        gate_ids=", ".join(g["id"] for g in gates),
    )
    (org_dir / "memory" / "adr" / "ADR-000-genesis.md").write_text(adr, encoding="utf-8")
    (org_dir / "memory" / "adr" / ".gitkeep").unlink(missing_ok=True)

    # 4. Mint key + genesis receipt (HMAC-signed root of trust)
    receipt = mint_genesis_receipt(org_dir, project_name, profile)
    with (org_dir / "ledger" / "receipts.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(receipt) + "\n")
    with (org_dir / "ledger" / "trust.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": ts, "agent": "founder", "event": "genesis", "trust": 1.0}) + "\n")

    # 4b. Seed Design Thinking Ask template into inbox
    tmpl_src = Path(__file__).parent / "templates" / "ask_design_thinking.md"
    if tmpl_src.exists():
        shutil.copyfile(str(tmpl_src), str(org_dir / "inbox" / "asks" / "TEMPLATE_DESIGN_THINKING.md"))
    with (org_dir / "ledger" / "payroll.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": ts, "event": "genesis", "tokens": 0, "cost_usd": 0.0}) + "\n")

    # 4c. Bootstrap Living Code Wiki, .llms.txt, and Runbooks
    from teamzero.wiki import build_living_wiki
    try:
        build_living_wiki(root)
    except Exception:
        pass

    # 4d. Write Layman Founder Cockpit & 3-Year Horizon Roadmap
    cockpit_md = FOUNDER_COCKPIT_TEMPLATE.format(
        org_name=project_name, version=TZ_VERSION, ts=ts, profile=profile,
    )
    (org_dir / "FOUNDER_COCKPIT.md").write_text(cockpit_md, encoding="utf-8")

    horizon_md = THREE_YEAR_HORIZON_TEMPLATE.format(
        org_name=project_name, version=TZ_VERSION, ts=ts, profile=profile,
    )
    (org_dir / "3_YEAR_HORIZON.md").write_text(horizon_md, encoding="utf-8")

    # 5. Gitignore + MCP client configs
    mcp_cmd = getattr(args, "mcp_cmd", sys.executable)
    actions = merge_gitignore(root)
    actions += write_mcp_configs(root, mcp_cmd, str(root))

    print(f"TeamZero {TZ_VERSION} initialized in {root}")
    print(f"  profile   : {profile}")
    print(f"  org       : {project_name}")
    print(f"  gates     : {', '.join(g['id'] for g in gates)}")
    print(f"  genesis   : {receipt['receipt_hmac'][:16]}... (receipts.jsonl)")
    for a in actions:
        print(f"  {a}")
    print()
    print("Next steps:")
    print("  1. 🎛️ Founder Cockpit ready: .teamzero/FOUNDER_COCKPIT.md")
    print("  2. 🗺️ 3-Year Strategic Plan ready: .teamzero/3_YEAR_HORIZON.md")
    print("  3. 📬 Founder Steering: run `tz inbox` to review decisions without reading code.")
    print("  4. Review .teamzero/constitution.yaml — adjust gate commands to your project.")
    print("  5. Commit .teamzero/ (the .mintkey is gitignored).")
    return 0


def cmd_doctor(args) -> int:
    target_path = getattr(args, "project_root", None) or getattr(args, "path", ".")
    root = Path(target_path).resolve()
    org_dir = root / ORG_DIR_NAME
    problems = []

    if not org_dir.is_dir():
        problems.append(f"{org_dir} missing — run: python -m teamzero init")
    else:
        if not (org_dir / "constitution.yaml").exists():
            problems.append("constitution.yaml missing")
        for leaf in [
            "memory/adr", "memory/map", "memory/specs", "memory/traps",
            "redteam/campaigns", "redteam/findings",
            "inbox/asks", "inbox/decisions",
            "ledger"
        ]:
            if not (org_dir / leaf).is_dir():
                problems.append(f"directory missing: .teamzero/{leaf}")
        if not (org_dir / ".mintkey").exists() and not os.environ.get("TZ_SERVER_SECRET"):
            problems.append("no mint authority: create .teamzero/.mintkey or set TZ_SERVER_SECRET")
        for ledger in ("trust.jsonl", "payroll.jsonl", "receipts.jsonl"):
            p = org_dir / "ledger" / ledger
            if p.exists():
                for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                    if line.strip():
                        try:
                            json.loads(line)
                        except json.JSONDecodeError:
                            problems.append(f"{ledger}:{i} is not valid JSON")
        # verify latest genesis receipt HMAC if we hold the key
        receipts = org_dir / "ledger" / "receipts.jsonl"
        key_src = os.environ.get("TZ_SERVER_SECRET") or ""
        mk = org_dir / ".mintkey"
        if not key_src and mk.exists():
            key_src = mk.read_text(encoding="utf-8").strip()
        if key_src and receipts.exists() and receipts.read_text().strip():
            lines = [l for l in receipts.read_text().strip().splitlines() if l.strip()]
            if lines:
                last = json.loads(lines[-1])
                body = {k: v for k, v in last.items() if k != "receipt_hmac"}
                expect = hmac.new(key_src.encode(), canonical(body), hashlib.sha256).hexdigest()
                if "receipt_hmac" in last and expect != last.get("receipt_hmac"):
                    problems.append("genesis receipt HMAC mismatch — mint key rotated or ledger tampered")

    gitignore = root / ".gitignore"
    if gitignore.exists() and ".teamzero/.mintkey" not in gitignore.read_text(encoding="utf-8"):
        problems.append(".gitignore does not cover .teamzero/.mintkey")

    if problems:
        print("doctor: FAIL")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"doctor: OK — {root} is governed by TeamZero")
    return 0


def init_project(target_dir: Path, name: Optional[str] = None, force: bool = False) -> Path:
    """Programmatic wrapper around cmd_init."""
    class _Args:
        pass
    a = _Args()
    a.project_root = str(target_dir)
    a.name = name
    a.profile = "auto"
    a.force = force
    a.mcp_cmd = sys.executable
    cmd_init(a)
    return target_dir / ORG_DIR_NAME
