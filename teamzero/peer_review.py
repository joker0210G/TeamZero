"""Peer Review Bot for TeamZero.

Translates Breaker findings and Evidence Graph records on a git diff into
clean, constructive, line-indexed GitHub Pull Request review drafts.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from teamzero.config import DECISIONS_DIR, ROOT_DIR


@dataclass
class ReviewComment:
    file_path: str
    line_number: int
    rule: str
    severity: str
    message: str
    suggested_fix: Optional[str] = None


class PeerReviewBot:
    """Generates structured PR review markdown drafts from breaker/evidence findings."""

    def __init__(self, decisions_dir: Optional[Path] = None):
        self.decisions_dir = decisions_dir or DECISIONS_DIR
        self.decisions_dir.mkdir(parents=True, exist_ok=True)

    def generate_review_markdown(
        self, branch: str, base_branch: str, comments: List[ReviewComment]
    ) -> Path:
        output_file = self.decisions_dir / f"review_{branch.replace('/', '_')}.md"

        crit_count = sum(1 for c in comments if c.severity in ["CRITICAL", "HIGH"])
        total_count = len(comments)

        lines = [
            f"# 🤖 TeamZero Automated Peer Review",
            f"**Branch:** `{branch}` (vs `{base_branch}`)",
            f"**Review Status:** {'❌ CHANGES REQUESTED' if crit_count > 0 else '✅ APPROVED WITH COMMENTS'}",
            f"**Summary:** {total_count} findings ({crit_count} blocking / high-severity).\n",
            "---",
            "### Inline Feedback\n",
        ]

        if not comments:
            lines.append("No defects, leaks, or quality breaches detected. Clean diff!")
        else:
            for c in comments:
                badge = "🔴" if c.severity == "CRITICAL" else ("🟠" if c.severity == "HIGH" else "🟡")
                lines.append(f"#### {badge} `{c.file_path}:{c.line_number}` — {c.rule} ({c.severity})")
                lines.append(f"> {c.message}\n")
                if c.suggested_fix:
                    lines.append("```suggestion")
                    lines.append(c.suggested_fix)
                    lines.append("```\n")

        content = "\n".join(lines)
        output_file.write_text(content, encoding="utf-8")
        return output_file
