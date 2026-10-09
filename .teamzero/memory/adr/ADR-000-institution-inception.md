# ADR-000: Institution Inception — The Autonomous AI Software Organization

## Status
Accepted

## Date
2026-10-09

## Context
Solo developers building software face a steep bottleneck: writing, testing, debugging, and maintaining code consumes all available runway. Vibe coding provides quick prototypes (~70%) but rapidly degrades into "slop coding" — unreviewed, fragile, insecure code with hallucinated packages and compounding technical debt.

Autonomous coding agents need more than role-play. They require an institutional operating system with machine-enforced governance, persistent memory, and cryptographic verification gates.

## Decision
We establish **TeamZero**: an autonomous agentic AI software organization with:
1. **Solo Founder / CEO Role**: The human developer manages priorities, resolves ambiguous design choices via the Asks Inbox, and serves as the ultimate authority.
2. **Autonomous Agent Employees**: Specialized roles (PM, Architect, Engineer, QA, Reviewer, Breaker) working on scoped tasks and isolated branches.
3. **The Institution as Product**:
   - Machine-enforced Quality Constitution (`.teamzero/constitution.yaml`)
   - Compounding Organizational Memory (`.teamzero/memory/`)
   - Adversarial Red Teaming & Anti-Slop Ratchet
   - Unified Operations CLI (`tz`)

### The Genesis Exception (Commit Zero)
A verification system cannot verify its own genesis. Commit zero has no prior commit SHA to key against, and remote branch protection cannot exist before the remote repository exists. 
Therefore, founder authority is exercised directly and deliberately for commit zero (`v0.1.0-bootstrap`). Every subsequent change—including all institutional, toolchain, and product code—must flow through the three-receipt merge gate.

## Consequences
- The founder never writes repetitive code or conducts manual line-by-line review.
- The organization can operate on zero initial budget using free-tier models and local execution.
- All institutional changes are recorded in immutable ledgers and ADRs.
- Clear boundary: Commit zero is sovereign genesis; all subsequent commits are constitutionally gated.
