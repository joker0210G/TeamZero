"""Time-Travel Debugger for TeamZero.

Allows rewinding execution to an exact journal sequence number, inspecting
the snapshot of evidence, findings, and ledger state at that instant,
and forking hypothetical states.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from teamzero.journal import EventJournal, JournalEvent


@dataclass
class ReplaySnapshot:
    run_id: str
    target_seq: int
    events_replayed: int
    reconstructed_state: Dict[str, Any]


class TimeTravelDebugger:
    """Reconstructs state up to any sequence number in an Event Journal."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.journal = EventJournal(run_id=run_id)

    def rewind_to(self, target_seq: int) -> ReplaySnapshot:
        """Reconstructs state by replaying events up to target_seq."""
        events = self.journal.read_events(up_to_seq=target_seq)

        state: Dict[str, Any] = {
            "findings": [],
            "trust_deltas": {},
            "active_tasks": {},
            "gate_verdicts": [],
        }

        for ev in events:
            p = ev.payload
            if ev.event_type == "finding_logged":
                state["findings"].append(p)
            elif ev.event_type == "trust_updated":
                peer = p.get("peer", "unknown")
                state["trust_deltas"][peer] = state["trust_deltas"].get(peer, 0.0) + p.get("delta", 0.0)
            elif ev.event_type == "task_started":
                state["active_tasks"][p.get("task_id")] = "IN_PROGRESS"
            elif ev.event_type == "task_completed":
                state["active_tasks"][p.get("task_id")] = "COMPLETED"
            elif ev.event_type == "gate_evaluated":
                state["gate_verdicts"].append(p)

        return ReplaySnapshot(
            run_id=self.run_id,
            target_seq=target_seq,
            events_replayed=len(events),
            reconstructed_state=state,
        )

    def fork_scenario(self, target_seq: int, overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a hypothetical fork starting from the target snapshot."""
        snapshot = self.rewind_to(target_seq)
        forked_state = dict(snapshot.reconstructed_state)
        forked_state.update(overrides)
        return {
            "base_run_id": self.run_id,
            "forked_at_seq": target_seq,
            "simulated_state": forked_state,
        }
