"""AI Red-Team Adversarial Spec Mutation Tester.

Red-Team agents craft subtle, devious logical mutant implementations
to aggressively test whether task specifications catch sneaky edge-case exploits.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class RedTeamMutant:
    mutant_id: str
    attack_vector: str
    description: str
    mutated_code: str


@dataclass
class MutationResult:
    total_mutants: int
    mutants_killed: int  # Caught by spec checks
    mutants_survived: int  # Tricked spec checks (spec blind spot!)
    spec_resilience_rating: float  # Percentage killed (0 - 100%)
    blind_spots: List[str]


class RedTeamMutationEngine:
    """Generates intelligent adversarial code mutations targeting spec edge cases."""

    def generate_adversarial_mutants(self, base_code: str) -> List[RedTeamMutant]:
        mutants: List[RedTeamMutant] = []

        # Vector 1: Precision / Currency truncation (financial rounding exploit)
        if "amount" in base_code:
            code_v1 = re.sub(r"float\(amount\)", "int(amount)", base_code)
            if code_v1 != base_code:
                mutants.append(
                    RedTeamMutant(
                        mutant_id="M_PRECISION_TRUNCATION",
                        attack_vector="financial_rounding_drift",
                        description="Truncates float amounts to int, losing fractional cents silently",
                        mutated_code=code_v1,
                    )
                )

        # Vector 2: Order-of-operations / Double-spend window
        if "balance >=" in base_code or "amount <=" in base_code:
            code_v2 = base_code.replace(">", ">=")
            mutants.append(
                RedTeamMutant(
                    mutant_id="M_BOUNDARY_OFF_BY_ONE",
                    attack_vector="boundary_leakage",
                    description="Relaxes strict inequality boundary check",
                    mutated_code=code_v2,
                )
            )

        # Vector 3: Silent Exception Swallowing (anti-pattern)
        if "raise ValueError" in base_code:
            code_v3 = base_code.replace("raise ValueError", "return {'status': 'ignored'}")
            mutants.append(
                RedTeamMutant(
                    mutant_id="M_SILENT_ERROR_SUPPRESSION",
                    attack_vector="silent_failure_bypass",
                    description="Replaces error raising with silent return payload",
                    mutated_code=code_v3,
                )
            )

        return mutants

    def evaluate_spec_resilience(
        self, mutants: List[RedTeamMutant], evaluator_fn: Any
    ) -> MutationResult:
        """Runs the evaluator function against each mutant.

        The evaluator_fn(mutated_code) should return True if tests pass (mutant SURVIVED = bad for spec),
        and False / raise Exception if tests fail (mutant KILLED = good for spec).
        """
        killed = 0
        survived = 0
        blind_spots: List[str] = []

        for m in mutants:
            try:
                passed = evaluator_fn(m.mutated_code)
                if passed:
                    # The mutant tricked the spec! Spec has a blind spot!
                    survived += 1
                    blind_spots.append(f"{m.mutant_id}: {m.description}")
                else:
                    killed += 1
            except Exception:
                # Exception raised means the test caught the mutant
                killed += 1

        total = len(mutants)
        rating = (killed / total * 100.0) if total > 0 else 100.0

        return MutationResult(
            total_mutants=total,
            mutants_killed=killed,
            mutants_survived=survived,
            spec_resilience_rating=rating,
            blind_spots=blind_spots,
        )
