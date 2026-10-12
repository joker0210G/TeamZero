"""Event Journal (Replay & Recovery) for TeamZero.

Logs immutable execution events per run.
Supports deterministic state replay and resumption without side-effect duplication.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from teamzero.config import JOURNAL_DIR


@dataclass
class JournalEvent:
    seq: int
    run_id: str
    event_type: str
    timestamp: float
    payload: Dict[str, Any]
    replay_mode: bool = False


class EventJournal:
    """Manages appending and replaying events for a run."""

    def __init__(self, run_id: str, journal_dir: Optional[Path] = None):
        self.run_id = run_id
        self.journal_dir = journal_dir or JOURNAL_DIR
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        self.journal_file = self.journal_dir / f"{run_id}.jsonl"
        self._seq = self._load_current_seq()

    def _load_current_seq(self) -> int:
        if not self.journal_file.exists():
            return 0
        lines = [line.strip() for line in self.journal_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            return 0
        try:
            last = json.loads(lines[-1])
            return int(last.get("seq", 0))
        except Exception:
            return len(lines)

    def emit(self, event_type: str, payload: Dict[str, Any]) -> JournalEvent:
        """Appends an event to the journal."""
        self._seq += 1
        event = JournalEvent(
            seq=self._seq,
            run_id=self.run_id,
            event_type=event_type,
            timestamp=time.time(),
            payload=payload,
            replay_mode=False,
        )
        with open(self.journal_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event)) + "\n")
        return event

    def read_events(self, up_to_seq: Optional[int] = None) -> List[JournalEvent]:
        """Reads all events up to an optional sequence number."""
        if not self.journal_file.exists():
            return []
        events: List[JournalEvent] = []
        for line in self.journal_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            ev = JournalEvent(**data)
            if up_to_seq is not None and ev.seq > up_to_seq:
                break
            events.append(ev)
        return events

    def replay_summary(self) -> Dict[str, Any]:
        """Provides a breakdown of all events in the run."""
        events = self.read_events()
        types: Dict[str, int] = {}
        for ev in events:
            types[ev.event_type] = types.get(ev.event_type, 0) + 1
        return {
            "run_id": self.run_id,
            "total_events": len(events),
            "last_seq": self._seq,
            "event_breakdown": types,
        }
