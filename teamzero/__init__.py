"""TeamZero: Autonomous Agentic AI Software Organization Foundation Package."""

__version__ = "1.0.0"

from teamzero.governance import (
    sign_receipt,
    verify_receipt,
    envelope,
    scan_for_poison,
    update_trust_score,
    load_constitution,
    record_payroll,
)
from teamzero.merge_gate import evaluate_merge_prerequisites, check_breaker_findings
from teamzero.refund_service import calculate_refund

__all__ = [
    "__version__",
    "sign_receipt",
    "verify_receipt",
    "envelope",
    "scan_for_poison",
    "update_trust_score",
    "load_constitution",
    "record_payroll",
    "evaluate_merge_prerequisites",
    "check_breaker_findings",
    "calculate_refund",
]
