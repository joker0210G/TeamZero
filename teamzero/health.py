"""Living SLA Dashboard & Health Engine for TeamZero.

Continuously assesses organizational health, SLA compliance (e.g. 24h critical finding resolution),
trust floors, and ratchet velocity, persisting status to .teamzero/health.json.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from teamzero.config import HEALTH_FILE, FINDINGS_DIR, TRUST_LEDGER


@dataclass
class HealthReport:
    timestamp: float
    overall_status: str  # HEALTHY, WARNING, CRITICAL_BREACH
    sla_breaches: List[str]
    unresolved_critical_count: int
    trust_violations: List[str]
    metrics: Dict[str, Any]


class SLADashboard:
    """Computes and tracks SLA compliance for TeamZero."""

    def __init__(self, health_file: Optional[Path] = None):
        self.health_file = health_file or HEALTH_FILE

    def compute_health(self) -> HealthReport:
        now = time.time()
        sla_breaches: List[str] = []
        unresolved_crit = 0

        # 1. Audit open findings for SLA breaches (> 24 hours = 86400s)
        if FINDINGS_DIR.exists():
            for fpath in FINDINGS_DIR.glob("*.json"):
                try:
                    data = json.loads(fpath.read_text(encoding="utf-8"))
                    findings = data.get("findings", [])
                    ts = data.get("timestamp", now)
                    for f in findings:
                        if f.get("severity") in ["CRITICAL", "HIGH"] and not f.get("resolved", False):
                            unresolved_crit += 1
                            age_hours = (now - ts) / 3600.0
                            if age_hours > 24.0:
                                sla_breaches.append(
                                    f"SLA Breach: Finding {f.get('rule')} ({f.get('severity')}) unresolved for {age_hours:.1f}h"
                                )
                except Exception:
                    pass

        # 2. Check trust floor breaches
        trust_violations: List[str] = []
        if TRUST_LEDGER.exists():
            try:
                for line in TRUST_LEDGER.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        t_data = json.loads(line)
                        score = t_data.get("new_score", 1.0)
                        peer = t_data.get("peer_id", "unknown")
                        if score < 0.4:
                            trust_violations.append(f"Trust Floor Alert: Peer '{peer}' trust dropped to {score:.2f}")
            except Exception:
                pass

        # Determine status
        if sla_breaches or unresolved_crit > 3:
            status = "CRITICAL_BREACH"
        elif unresolved_crit > 0 or trust_violations:
            status = "WARNING"
        else:
            status = "HEALTHY"

        report = HealthReport(
            timestamp=now,
            overall_status=status,
            sla_breaches=sla_breaches,
            unresolved_critical_count=unresolved_crit,
            trust_violations=trust_violations,
            metrics={"unresolved_critical": unresolved_crit, "sla_breach_count": len(sla_breaches)},
        )

        self._save_health(report)
        return report

    def _save_health(self, report: HealthReport) -> None:
        self.health_file.parent.mkdir(parents=True, exist_ok=True)
        self.health_file.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
