# Onboarding Runbook: Developer & Agent Workflow

## 1. Quickstart Commands
- **Environment Doctor**: `python -m teamzero.cli doctor`
- **Living Status**: `python -m teamzero.cli status`
- **Active Task Navigator**: `python -m teamzero.cli task next`
- **Design Thinking Ideator**: `python -m teamzero.cli ideate`
- **Living Code Wiki**: `python -m teamzero.cli docs build`

## 2. Invariants & Rules
Every change must be validated against the Quality Constitution (`.teamzero/constitution.yaml`).
Autonomous agents cannot self-merge; merge requires HMAC-signed gauntlet receipts.

## 3. Local Environment Quirks
- On Windows PowerShell, verify execution policy or invoke via `python -m teamzero.cli`.
- MCP server runs via `python -m teamzero.mcp_server`.
