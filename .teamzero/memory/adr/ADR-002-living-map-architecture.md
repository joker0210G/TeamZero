# ADR-002: Living Codebase Map & Forensics Architecture

## Status
Accepted

## Context
As an autonomous AI organization generates and updates code across repositories, human founders risk losing structural understanding of their codebase ("the opacity trap"). Debugging turns into trial-and-error, and context windows are wasted feeding entire directories into prompts.

## Decision
1. TeamZero maintains **Living Module Map cards** (`.teamzero/memory/map/{module}.md`) defining for each component:
   - Purpose and ownership
   - Public contract (inputs, outputs, exceptions)
   - Invariants and preconditions
   - Known traps and failure modes
   - Upstream and downstream dependencies
2. Map cards are automatically synchronized on merge from code inspection. Manual edits to map cards are prohibited to prevent context poisoning.
3. When incidents or failures occur, the Forensics pipeline compiles a **Diagnosis Packet** (reproduction, call trace, violated invariants) directly into the founder's Asks Inbox.

## Consequences
- Agents on-board into submodules by reading lightweight module cards (<300 tokens) instead of parsing entire repositories.
- Keeps token consumption minimal for solo developers operating on free tiers.
