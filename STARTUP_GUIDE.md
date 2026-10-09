# TeamZero: Solo Founder's Zero-Budget Field Manual

> A practical guide for operating an autonomous AI software company on a low-end PC using free-tier models (Google Antigravity, OpenRouter Free).

---

## 🎯 The Solo Developer Reality

Most multi-agent frameworks fail solo developers because they consume millions of tokens on verbose role-playing dialogues between agents before producing a single line of code.

TeamZero solves this through **Extreme Token Economization** and **Deterministic Gatekeeping**:
1. **CPU & Heuristics First ($0)**: Static linters, boundary sweeps, and regex patterns cost 0 tokens and run locally in milliseconds.
2. **Context Compression ($0.00)**: Agents never read entire repositories. They read Living Map Cards (<300 tokens) and formal Executable Specifications.
3. **The Ratchet Mechanism**: When an LLM catches a novel bug once, TeamZero compiles that pattern into a deterministic check so it is caught for free forever after.

---

## 📋 The Founder Operating Workflow

```
[ Founder Intake ]
       │ (1 napkin prompt / issue)
       ▼
[ PM / Architect ] ──► Produces Executable Spec (.teamzero/memory/specs/*.json)
       │
       ▼
[ QA Agent ] ────────► Authors acceptance test cases against Spec (Tests first!)
       │
       ▼
[ Engineer Agent ] ──► Implements code on isolated branch
       │
       ▼
[ Deterministic Gauntlet ] ──► Syntax, pytest, secret scan ($0 tokens)
       │ (Pass)
       ▼
[ L1 Breaker Pass ] ─────────► Boundary sweeps, mutations, risk prober ($0 - ~2k tokens)
       │
   ┌───┴────────────────────────┐
   │                            │
(Pass)                       (Defects)
   │                            │
[ Signed HMAC Receipt ]      [ Needs Repair ] (Max 3 attempts)
   │                            │ (Exhausted)
[ Auto-Merge by CI ]         [ Asks Inbox ] ──► Founder makes 1 decision over coffee
```

---

## 💡 Token-Saving Context Engineering Rules

### 1. Distilled Role Cards (<200 Tokens)
Avoid passing multi-page role descriptions. TeamZero uses concise operational contracts:
```text
Role: BREAKER (Adversarial Reviewer).
Task: Prove candidate is NOT done against attached Spec.
Priority: Boundary values, negative/None inputs, spec silence, concurrency.
Output: Strict JSON hypotheses only.
```

### 2. Instruction / Data Isolation
Always wrap reference materials in the `<<<TEAMZERO-DATA-v1>>>` envelope. This stops models from wandering off into meta-commentary or attempting prompt injections embedded in third-party text.

### 3. Asks Inbox Batching
Do not sit in a live chat loop with your agents. Let them work asynchronously against git branches. Check `.teamzero/inbox/asks/` once or twice a day:
- Read 3-5 structured decision requests.
- Provide yes/no or select option A/B.
- Let the organization resume autonomous execution.

---

## 🛠️ Step-by-Step Daily Commands (`tz`)

1. **Check Organization Status & Trust Scores**:
   ```bash
   python tz.py status
   ```
2. **Review & Batch Decisions in Asks Inbox**:
   ```bash
   python tz.py inbox
   ```
3. **Compile Specs into Test Suites ($0 Tokens)**:
   ```bash
   python tz.py spec
   ```
4. **Run Deterministic Gauntlet & Sign Receipt**:
   ```bash
   python tz.py gauntlet
   ```
5. **Trigger Breaker Verification Pass**:
   ```bash
   python tz.py breaker --demo
   ```
6. **Evaluate Cryptographic Merge Prerequisites**:
   ```bash
   python tz.py check-merge
   ```
7. **Start MCP Server for Cursor / Claude Code / Antigravity**:
   ```bash
   python mcp_server.py
   ```
