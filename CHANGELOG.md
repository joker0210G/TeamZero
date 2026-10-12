# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0-alpha.1] - 2026-10-12

### Added
- **Typed Evidence Graph** (`teamzero/evidence.py`): Persistent evidence nodes stored in `.teamzero/memory/evidence/` with lineage tracking across tasks and generations.
- **Merge Gate Evidence Integration** (`teamzero/merge_gate.py`): Cryptographic merge gate now blocks if unresolved CRITICAL or HIGH evidence nodes exist for a candidate task.
- **Evidence-Weighted Trust Decay** (`teamzero/governance.py`): 2× trust penalty applied when agents repeat known defects recorded in the Evidence Graph.
- **Task-Owned Evaluator Engine** (`teamzero/evaluator.py`): Composite evaluation (pytest, latency ceiling, and evidence resolution) configured directly within spec JSONs.
- **Generational Research Loops** (`teamzero/generation.py`): Multi-generation task states with inherited constraints and cumulative token tracking.
- **Parallel Hypothesis Racing** (`teamzero/racing.py`): Multi-peer exploration CLI (`tz race`) evaluating competing implementation strategies against specs.
- **ADR Auto-Synthesis** (`teamzero/synthesize.py`): Automated synthesis generation (`tz synthesize`) updating Living Map cards and emitting permanent ADR records.
- **Canary Lineage Tracker** (`teamzero/canary_lineage.py`): Security breach tracing correlating leaks back to agent, task, commit, and evidence nodes.
- **Smart Inbox Batching** (`teamzero/inbox_triage.py`): Task-level clustering for founder decision triage.
- **Self-Healing Ratchet** (`teamzero/ratchet.py`): Health auditing (`tz ratchet --health`) with automatic rule promotion from resolved evidence nodes.
- **Unified CLI Additions** (`tz.py`): Added `budget`, `evidence`, `race`, `synthesize`, `canary`, and `ratchet` subcommands.
- **Comprehensive Unit Tests** (`tests/test_evidence_graph.py`): Verification suites for evidence graph recording, querying, resolution, and merge gate enforcement.
- **Initial Core Architecture**: Deterministic Gauntlet, L1 Breaker, FastMCP Server, and Quality Constitution.

### Changed
- `l1_pass.py`: Breaker run now persists all probe findings into the Typed Evidence Graph and applies evidence-weighted trust decay.
- `campaign_runner.py`: Canary leaks now automatically register in the Canary Lineage Tracker.
