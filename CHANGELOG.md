# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0-alpha.2] - 2026-10-12

### Added
- **Event Journal & Replay Engine** (`teamzero/journal.py`, `tz replay <run_id>`): Immutable event-sourced logging of all execution steps with safe state resumption and deduplication of side effects.
- **Time-Travel Debugger** (`teamzero/debugger.py`, `tz debug-at <seq>`): Step-by-step state rewind, inspection of active evidence/trust at any point in history, and hypothetical scenario forking.
- **Pareto Scoreboard** (`teamzero/pareto.py`, `tz pareto`): Multi-objective non-dominated frontier evaluation (speed, coverage, memory efficiency) preserving nuance and architectural trade-offs.
- **Solution Diversity Guard** (`teamzero/diversity.py`): Architectural niche classification preventing premature convergence and maintaining diverse exploration strategies in hypothesis pools.
- **Multi-Provider Model Router** (`teamzero/model_router.py`, `tz route`): Dynamic tier allocation (`lite`, `standard`, `frontier`) with customizable provider selection (Gemini, Anthropic, OpenAI, Local Ollama) via `.teamzero/providers.yaml`.
- **Adaptive Catch-Up Trigger Engine** (`teamzero/triggers.py`, `tz triggers`): Missed-interval detection tailored for dynamic, irregular PC sessions with opportunistic background catch-up execution.
- **AI Red-Team Adversarial Spec Mutation Tester** (`teamzero/mutation.py`, `tz mutate`): Intelligent adversarial stress-testing employing Red Team agents to expose spec blind spots via order inversion, race simulation, and silent error suppression.
- **Living SLA & Health Dashboard** (`teamzero/health.py`, `tz health`): 24-hour critical issue countdown and automated organizational health monitoring persisted to `.teamzero/health.json`.
- **XZ-Grade Supply-Chain Defense Scanner** (`teamzero/supply_chain.py`, `tz dep-scan`): Detection of hidden test payloads in binary fixtures (CVE-2024-3094 vector), build hook inspection, and Levenshtein dependency typosquat analysis.
- **Peer Review Bot** (`teamzero/peer_review.py`, `tz review <branch>`): Automated conversion of breaker findings into structured, line-annotated GitHub PR review markdown drafts.
- **Comprehensive Verification Suite** (`tests/test_round2_improvements.py`): 9 comprehensive unit and integration tests verifying all 10 Round 2 systems.

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
