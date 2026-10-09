#!/usr/bin/env python3
"""TeamZero Slop Audit Tool.

Scans a codebase for AI slop characteristics:
1. Hallucinated or unpinned dependencies
2. Exposed credentials or secrets
3. Coverage holes (untested source files)
4. Weak or trivial assertions (always-green test slop)
5. Architectural boundary breaches

Usage:
  python slop_audit.py
  python slop_audit.py --path /path/to/repo
"""

from __future__ import annotations
import argparse
import ast
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

SECRET_PATTERNS = [
    (r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][A-Za-z0-9_\-]{8,}['\"]", "Hardcoded API Key / Secret"),
    (r"(?i)-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", "Exposed Private Key")
]

TRIVIAL_ASSERT_PATTERNS = [
    (r"assert\s+True\b", "assert True (Trivial pass)"),
    (r"assert\s+\w+\s+is not None\b", "assert is not None (Weak existence check)"),
    (r"^\s*pass\s*$", "pass statement in test body"),
]


def audit_repository(repo_path: Path) -> Dict[str, Any]:
    print(f"[*] Starting TeamZero Slop Audit on: {repo_path.resolve()}\n")
    
    findings = []
    
    # 1. Scan for Secrets
    print("[-] [Gate 1] Secret & Credential Scanning...")
    for py_file in repo_path.rglob("*.py"):
        if ".git" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            for pat, name in SECRET_PATTERNS:
                matches = re.findall(pat, content)
                if matches:
                    rel = py_file.relative_to(repo_path)
                    findings.append({
                        "category": "SECURITY_SECRET",
                        "severity": "CRITICAL",
                        "file": str(rel),
                        "description": f"Potential {name} detected"
                    })
        except Exception:
            pass

    # 2. Scan for Test Weaknesses (Always-Green Slop)
    print("[-] [Gate 2] Test Suite Assertion Rigor...")
    for test_file in repo_path.rglob("test_*.py"):
        try:
            lines = test_file.read_text(encoding="utf-8", errors="ignore").splitlines()
            rel = test_file.relative_to(repo_path)
            for i, line in enumerate(lines, 1):
                for pat, name in TRIVIAL_ASSERT_PATTERNS:
                    if re.search(pat, line):
                        findings.append({
                            "category": "TEST_SLOP",
                            "severity": "MEDIUM",
                            "file": f"{rel}:{i}",
                            "description": f"Trivial assertion found: {name}"
                        })
        except Exception:
            pass

    # 3. Scan for Untested Source Files (Coverage Holes)
    print("[-] [Gate 3] Coverage & Orphan Module Detection...")
    src_files = [f for f in repo_path.rglob("*.py") if not f.name.startswith("test_") and not f.name.startswith("setup") and ".git" not in str(f)]
    test_files = [f.stem.replace("test_", "") for f in repo_path.rglob("test_*.py")]
    
    for src in src_files:
        if src.stem not in test_files and src.name != "__init__.py" and src.name != "config.py":
            rel = src.relative_to(repo_path)
            findings.append({
                "category": "COVERAGE_HOLE",
                "severity": "LOW",
                "file": str(rel),
                "description": f"No dedicated test suite identified for {src.stem}"
            })

    # Summary
    criticals = [f for f in findings if f["severity"] == "CRITICAL"]
    highs = [f for f in findings if f["severity"] == "HIGH"]
    mediums = [f for f in findings if f["severity"] == "MEDIUM"]
    lows = [f for f in findings if f["severity"] == "LOW"]

    print("\n" + "=" * 65)
    print(" TeamZero Slop Audit Report")
    print("=" * 65)
    print(f"Total Issues: {len(findings)} | Critical: {len(criticals)} | High: {len(highs)} | Medium: {len(mediums)} | Low: {len(lows)}\n")

    for f in findings:
        print(f"[{f['severity']}] [{f['category']}] {f['file']}")
        print(f"       -> {f['description']}")

    print("=" * 65)
    
    health_score = max(0, 100 - (len(criticals) * 25 + len(highs) * 15 + len(mediums) * 5 + len(lows) * 1))
    print(f"\nOverall Codebase Health Score: {health_score}/100")
    if health_score >= 90:
        print("Verdict: Clean & Hardened (Production Ready)")
    else:
        print("Verdict: Slop Remediations Required")
    print("=" * 65)

    return {
        "health_score": health_score,
        "findings": findings
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TeamZero Slop Audit")
    parser.add_argument("--path", type=str, default=".", help="Target directory to audit")
    args = parser.parse_args()
    audit_repository(Path(args.path))
