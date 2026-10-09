# TeamZero: Autonomous Agentic AI Software Organization

> *"Your engineering department for the price of a few subscriptions — or zero initial budget."*

TeamZero is an autonomous agentic software organization architecture designed for a **solo human founder/CEO** orchestrating specialized AI agents. Rather than relying on fragile "vibe coding" without quality gates, TeamZero implements an institutional operating system that treats every generated line of code as guilty until proven passing.

---

## 🏛️ The Three Moats

1. **Verification Over Trust**: No agent has authority to merge code. "Done" is computed strictly by automated deterministic pipelines and adversarial Red Team breakers, never asserted by an LLM.
2. **Organizational Memory**: Specifications, Architecture Decision Records (ADRs), Living Module Maps, and known failure traps persist across sessions and compound in value over time.
3. **The Founder Experience**: You manage like a CEO, not a prompt engineer. Ambiguous decisions escalate into your **Asks Inbox**, while autonomous work proceeds within calibrated trust boundaries.

---

## 📁 Repository Structure

```
TeamZero/
├── .teamzero/                        # Institutional Governance Layer
│   ├── constitution.yaml             # Machine-enforced Quality Constitution
│   ├── memory/                       # Persistent Organizational Memory
│   │   ├── adr/                      # Architecture Decision Records (ADR-001..003)
│   │   ├── map/                      # Living Module Map Cards (refund.md)
│   │   ├── specs/                    # Executable Specifications (refund_spec.json)
│   │   └── traps/                    # Domain anti-patterns and known traps
│   ├── redteam/                      # Adversarial Security & Stress Testing
│   │   ├── campaigns/                # L2/L3 War Game scenarios (ctx-poison-001.yaml)
│   │   └── findings/                 # Machine-verifiable Diagnosis Packets
│   ├── inbox/                        # Founder Escalation Queues
│   │   ├── asks/                     # Asks Inbox for ambiguous business decisions
│   │   └── decisions/                # Proposed ADRs awaiting human approval
│   └── ledger/                       # Immutable Operational Ledgers
│       ├── trust.jsonl               # Agent trust scores & calibrated autonomy
│       ├── payroll.jsonl             # Token burn & compute cost tracking
│       └── receipts.jsonl            # HMAC-SHA256 cryptographic receipts
│
├── teamzero/                         # Core Python Package
│   ├── config.py                     # Path and environment configuration
│   ├── governance.py                 # Cryptographic receipts & trust engine
│   └── refund_service.py             # Reference implementation adhering to SPEC
│
├── tests/                            # Quality Gauntlet Test Suites
│   └── test_refund.py                # Acceptance tests derived from specs
│
├── l1_pass.py                        # L1 Red Team Breaker Run (Phases A, B, C, D)
├── mcp_server.py                     # Model Context Protocol (FastMCP) Server
├── campaign_runner.py                # L2/L3 War Game & Canary Leak Runner
├── slop_audit.py                     # Anti-Slop Audit & Codebase Health Scanner
│
├── .cursor/mcp.json                  # Cursor MCP Configuration
├── claude_mcp.json                   # Claude Code MCP Configuration
├── antigravity_mcp.json              # Antigravity MCP Configuration
├── .github/workflows/gauntlet.yml     # Automated CI Merge Gauntlet
├── STARTUP_GUIDE.md                  # Solo Developer Zero-Budget Manual
└── README.md                         # Architecture Overview & Reference
```

---

## ⚡ Quickstart

### 1. Run the Deterministic Quality Gauntlet
Verify syntax, unit test suite, and invariant assertions:
```bash
python -m pytest tests/
```

### 2. Run the Red Team Breaker Pass (Demo Mode - $0 Tokens)
Test how the L1 Breaker catches latent off-by-one errors and unguarded inputs completely offline:
```bash
python l1_pass.py --demo --offline
```

### 3. Run War Game Scenarios & Canary Tracking
Execute L2 context-poisoning campaigns to verify sentinel defenses:
```bash
python campaign_runner.py --all
```

### 4. Run the Anti-Slop Codebase Audit
Scan your project for exposed secrets, coverage holes, and weak assertions:
```bash
python slop_audit.py
```

---

## 🔌 Model Context Protocol (MCP) Integration

TeamZero exposes itself as an MCP server under the **"Lobby, Not A Vault"** security model ([ADR-003](file:///.teamzero/memory/adr/ADR-003-mcp-lobby-vault-boundary.md)):

### Exposed Tools
| Tool | Access | Description |
|---|---|---|
| `teamzero_query_memory` | Read | Search ADRs, specs, maps, and traps inside safe envelopes |
| `teamzero_get_spec` | Read | Fetch formal executable specifications |
| `teamzero_run_gauntlet` | Action | Dispatch deterministic test suite & receive HMAC receipt |
| `teamzero_submit_candidate` | Action | Run gauntlet + L1 Breaker; returns findings packet |
| `teamzero_get_findings` | Read | Lookup canonical server-side findings for a commit SHA |
| `teamzero_file_decision` | Proposal | Propose an ADR into the founder review inbox |
| `teamzero_ask_founder` | Comms | Post a clarification request into the founder's Asks Inbox |

### Intentionally Absent (Security Invariants)
- ❌ **`teamzero_merge`**: Does not exist. Merge authority belongs exclusively to the CI bot.
- ❌ **`teamzero_set_done`**: Does not exist. "Done" is derived from passing gate receipts.
- ❌ **Direct write to memory/constitution**: Memory files are write-protected against agents.

### Connecting External Agents
- **Cursor**: Use [`.cursor/mcp.json`](file:///.cursor/mcp.json)
- **Claude Code**: Run `claude mcp add teamzero -- python d:/Workspace/TeamZero/mcp_server.py`
- **Google Antigravity**: Add [`antigravity_mcp.json`](file:///antigravity_mcp.json)

---

## 🛡️ Anti-Slop Defense Invariants

1. **The Generator Never Verifies**: Author agents and reviewer agents operate on distinct prompts and model families.
2. **QA Sees The Spec, Never The Diff**: Acceptance tests are derived from the specification before code inspection, preventing confirmation bias.
3. **Done Is Computed, Never Asserted**: State machines advance only when CI emits cryptographically signed receipts.
4. **Sandboxes Hold No Secrets**: Credentials are injected solely at runtime in isolated environments; protected constitution paths are read-only.
5. **Failure Has A Price**: Uncaught bugs decay agent trust scores and dock task token budgets.
