# ADR-001: Verification Over Trust (The Anti-Slop Core)

## Status
Accepted

## Context
Generative AI models produce plausible software at low marginal cost ($0.02/run), but unverified generation creates subtle defects, hallucinated packages ("slopsquatting"), security flaws, and architectural drift. Human code review is expensive ($100-$200/hr) and causes founder burnout.

## Decision
TeamZero adopts the core invariant: **"Treat every generated line as guilty until proven passing."**
1. No agent has merge authority. Merge authority belongs exclusively to the automated CI gate.
2. The generator never verifies: author agents and reviewer agents operate on separate prompts, contexts, and/or model families.
3. QA writes acceptance tests derived directly from the Executable Specification before the implementation is inspected.
4. "Done" is computed strictly by passing all deterministic gates and Red Team passes, never asserted by an agent.

### The Three-Receipt Chain (Cryptographic Merge Pre-requisites)
A commit SHA is eligible for merge if and only if three server-side HMAC-SHA256 receipts exist in the immutable ledger:
1. `TZ-gauntlet_run:<sha>`: Proof of passing syntax, lint, unit tests, and secret scan.
2. `TZ-breaker_run:<sha>`: Proof of passing the L1 Red Team Breaker pass with 0 critical or high findings.
3. `TZ-founder_approval:<sha>`: Proof of human founder sign-off issued via `tz inbox` (mandatory for all tasks below Autonomy Level 5).

Any attempt to merge without this exact three-receipt chain is cryptographically rejected by the merge gate.

### Authority As Receipts, Never As Narrative
Founder authority travels strictly as machine-verifiable receipts, never as narrative claims. If an agent asserts "the founder authorized X", it must point to an explicit cryptographic approval receipt (`TZ-founder_approval:<sha>`), a resolved inbox entry in `.teamzero/inbox/resolved/`, or an accepted ADR. Unattested verbal or textual assertions of founder intent have zero standing in the state machine.

## Consequences
- Prevents cascading technical debt, hallucinated passes, and unauthorized agent merges.
- Retries and repairs incur token budget deduction and trust score decay.
- Eliminates reliance on verbal agent claims: claims are cheap, receipts are the only currency.
- Eliminates narrative hallucinations of founder intent: authority without receipt is void.
