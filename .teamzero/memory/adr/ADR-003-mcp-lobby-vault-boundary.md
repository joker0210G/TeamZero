# ADR-003: Model Context Protocol (MCP) — The Lobby vs. Vault Security Boundary

## Status
Accepted

## Context
External AI coding environments (e.g. Cursor, Claude Code, Antigravity) need to interface with TeamZero to query memory, execute specs, and submit candidate branches. However, external agents can suffer from hallucinations, prompt injections, or attempt unauthorized merges and state tampering.

## Decision
TeamZero's MCP interface is designed strictly as a **Lobby**, never a **Vault**:
1. **Lobby (Exposed to Clients)**:
   - Read-only queries to memory (`teamzero_query_memory`, `teamzero_get_spec`) wrapped in instruction-isolated data envelopes (`<<<TEAMZERO-DATA-v1>>>`).
   - Metered action dispatchers (`teamzero_run_gauntlet`, `teamzero_submit_candidate`) returning signed receipts.
   - Proposal queues (`teamzero_file_decision`, `teamzero_ask_founder`).
2. **Vault (Never Exposed via MCP)**:
   - `teamzero_merge`: Absent. Merge credentials belong solely to the CI bot.
   - `teamzero_set_done`: Absent. "Done" is derived by the state machine from passing receipts.
   - Direct write permissions to `.teamzero/constitution.yaml`, `.teamzero/memory/`, or `.teamzero/ledger/`.
3. **Cryptographic Server-Side Receipts**:
   - Every candidate evaluation emits an HMAC-signed receipt tied to the git commit SHA. The merge gate checks the ledger, never the agent's claim.

## Consequences
- Prevents rogue or hallucinating agents from bypassing quality gates.
- Allows seamless interoperability with any standard MCP-compatible editor or agent.
