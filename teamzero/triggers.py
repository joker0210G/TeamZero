"""Adaptive Catch-Up Trigger Engine for TeamZero.

Designed for dynamic and irregular PC sessions:
- Detects missed periodic cadences (daily audit, weekly canary check) across reboots.
- Supports opportunistic warmup catch-ups without locking terminal UI.
- File-change reactive triggers when developer touches source or specs.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from teamzero.config import TRIGGERS_DIR

STATE_FILE = TRIGGERS_DIR / "state.json"
REGISTRY_FILE = TRIGGERS_DIR / "triggers.json"

DEFAULT_TRIGGERS = [
    {
        "id": "daily_audit",
        "description": "Daily anti-slop code audit",
        "interval_seconds": 86400,  # 24 hours
        "command": "audit",
    },
    {
        "id": "canary_rotation",
        "description": "Weekly canary token lineage check",
        "interval_seconds": 604800,  # 7 days
        "command": "canary",
    },
]


@dataclass
class TriggerStatus:
    trigger_id: str
    last_run_timestamp: float
    next_due_timestamp: float
    status: str  # DUE, OK, MISSED_OVERDUE


class AdaptiveTriggerEngine:
    """Evaluates scheduled triggers and determines catch-up needs."""

    def __init__(self, triggers_dir: Optional[Path] = None):
        self.triggers_dir = triggers_dir or TRIGGERS_DIR
        self.triggers_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.triggers_dir / "state.json"
        self.registry_file = self.triggers_dir / "triggers.json"
        self.triggers = self._load_triggers()
        self.state = self._load_state()

    def _load_triggers(self) -> List[Dict[str, Any]]:
        if self.registry_file.exists():
            try:
                return json.loads(self.registry_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        self.registry_file.write_text(json.dumps(DEFAULT_TRIGGERS, indent=2), encoding="utf-8")
        return DEFAULT_TRIGGERS

    def _load_state(self) -> Dict[str, float]:
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_state(self) -> None:
        self.state_file.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def record_run(self, trigger_id: str) -> None:
        """Records a successful trigger execution timestamp."""
        self.state[trigger_id] = time.time()
        self._save_state()

    def evaluate_triggers(self, current_time: Optional[float] = None) -> List[TriggerStatus]:
        """Evaluates triggers and reports which are overdue for opportunistic catch-up."""
        now = current_time or time.time()
        results: List[TriggerStatus] = []

        for trig in self.triggers:
            tid = trig["id"]
            interval = trig.get("interval_seconds", 86400)
            last_run = self.state.get(tid, 0.0)
            next_due = last_run + interval

            if last_run == 0.0:
                status = "DUE"
            elif now >= next_due:
                # Missed while PC was off or idle
                status = "MISSED_OVERDUE"
            else:
                status = "OK"

            results.append(
                TriggerStatus(
                    trigger_id=tid,
                    last_run_timestamp=last_run,
                    next_due_timestamp=next_due,
                    status=status,
                )
            )

        return results

    def get_pending_catchups(self) -> List[Dict[str, Any]]:
        """Returns list of triggers that should catch up now."""
        statuses = {s.trigger_id: s.status for s in self.evaluate_triggers()}
        pending = []
        for trig in self.triggers:
            if statuses.get(trig["id"]) in ["DUE", "MISSED_OVERDUE"]:
                pending.append(trig)
        return pending
