"""Pareto Scoreboard and Multi-Objective Trade-Off Evaluation.

Calculates the Pareto-optimal frontier among competing hypotheses or code solutions.
A solution dominates another if it is >= on all objectives and strictly > on at least one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class SolutionCandidate:
    candidate_id: str
    metrics: Dict[str, float]  # Higher is better for all metrics normalized here
    metadata: Dict[str, Any]


def dominates(a: SolutionCandidate, b: SolutionCandidate, metrics_keys: List[str]) -> bool:
    """Returns True if candidate `a` Pareto-dominates candidate `b`."""
    at_least_as_good = True
    strictly_better = False

    for m in metrics_keys:
        val_a = a.metrics.get(m, 0.0)
        val_b = b.metrics.get(m, 0.0)
        if val_a < val_b:
            at_least_as_good = False
            break
        if val_a > val_b:
            strictly_better = True

    return at_least_as_good and strictly_better


def compute_pareto_front(
    candidates: List[SolutionCandidate], metrics_keys: List[str]
) -> List[SolutionCandidate]:
    """Extracts non-dominated solutions from the candidate pool."""
    pareto_front: List[SolutionCandidate] = []

    for candidate in candidates:
        dominated = False
        for other in candidates:
            if candidate.candidate_id == other.candidate_id:
                continue
            if dominates(other, candidate, metrics_keys):
                dominated = True
                break
        if not dominated:
            pareto_front.append(candidate)

    return pareto_front


def format_scoreboard(front: List[SolutionCandidate], metrics_keys: List[str]) -> str:
    """Renders a readable summary table of the Pareto front."""
    if not front:
        return "No Pareto candidates available."

    header = f"{'Candidate ID':<25} | " + " | ".join(f"{k:<12}" for k in metrics_keys)
    divider = "-" * len(header)
    rows = [header, divider]

    for c in front:
        metric_str = " | ".join(f"{c.metrics.get(k, 0.0):<12.2f}" for k in metrics_keys)
        rows.append(f"{c.candidate_id:<25} | {metric_str}")

    return "\n".join(rows)
