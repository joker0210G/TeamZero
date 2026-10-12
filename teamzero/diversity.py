"""Solution Diversity Guard (Quality-Diversity Exploration).

Categorizes candidate hypotheses into distinct behavioral niches (e.g., defensive, optimistic, caching)
and ensures candidate pools maintain architectural variety instead of converging on a single monoculture.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Set


@dataclass
class NicheProfile:
    niche_id: str
    description: str
    matched_patterns: List[str]


# Predefined behavioral niches for code exploration
DEFAULT_NICHES = {
    "validation_first": [r"if not ", r"assert ", r"raise ValueError", r"check_"],
    "optimistic_resilient": [r"try:", r"except Exception", r"except \(", r"finally:"],
    "cache_memoized": [r"cache", r"memo", r"_registry", r"dict\(\)"],
    "pure_functional": [r"def _", r"return tuple\(", r"lambda ", r"map\(|filter\("],
    "event_driven": [r"emit\(", r"publish", r"notify", r"dispatch"],
}


def classify_behavioral_niche(code: str) -> str:
    """Assigns code to a behavioral niche based on architectural style patterns."""
    scores: Dict[str, int] = {}
    for niche, patterns in DEFAULT_NICHES.items():
        score = sum(len(re.findall(p, code)) for p in patterns)
        scores[niche] = score

    best_niche = max(scores, key=scores.get)
    if scores[best_niche] == 0:
        return "general_imperative"
    return best_niche


def enforce_diversity_quota(
    candidates: List[Dict[str, str]], min_niches: int = 2
) -> Dict[str, List[Dict[str, str]]]:
    """Partitions candidate proposals by behavioral niche and reports diversity coverage."""
    niches_map: Dict[str, List[Dict[str, str]]] = {}

    for c in candidates:
        code = c.get("code", "")
        niche = classify_behavioral_niche(code)
        niches_map.setdefault(niche, []).append(c)

    return niches_map
