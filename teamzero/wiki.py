"""Living Code Wiki & Docs-as-Code Engine for TeamZero.

Inspired by Google's Code Wiki and the human-crafted Docs-as-Code strategy:
1. Treats code as the source of truth for syntactic structure (AST extraction).
2. Outperforms automated code wikis by anchoring the "Why" (ADRs, trade-offs, traps, invariants).
3. Produces flat-file curated indices: .llms.txt and wiki.json for zero-latency LLM navigation.
4. Treats documentation like a Bonsai Tree: automated pruning of stale cards and dead links.
5. Enforces Docs-as-Code PR gatekeeping: flags documentation drift when code changes without doc updates.
6. Maintains operational playbooks and disaster recovery runbooks.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from teamzero.config import (
    ROOT_DIR,
    ORG_DIR,
    MEMORY_DIR,
    ADR_DIR,
    MAP_DIR,
    SPECS_DIR,
    TRAPS_DIR,
    WIKI_DIR,
    RUNBOOKS_DIR,
    LLMS_TXT_FILE,
    WIKI_JSON_FILE,
    CONSTITUTION_FILE,
)


@dataclass
class SymbolContract:
    name: str
    kind: str  # class | function | method | constant
    docstring: str = ""
    signature: str = ""
    line_number: int = 0
    decorators: List[str] = field(default_factory=list)


@dataclass
class ModuleManifest:
    module_name: str
    file_path: str
    docstring: str
    classes: List[SymbolContract] = field(default_factory=list)
    functions: List[SymbolContract] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    adr_citations: List[str] = field(default_factory=list)
    has_traps: bool = False
    has_spec: bool = False
    last_updated: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


def extract_module_symbols(file_path: Path) -> ModuleManifest:
    """Extracts classes, functions, docstrings, and contracts via Python AST."""
    manifest = ModuleManifest(
        module_name=file_path.stem,
        file_path=str(file_path.resolve()),
        docstring=""
    )

    if not file_path.exists() or not file_path.suffix == ".py":
        return manifest

    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except Exception as e:
        manifest.docstring = f"[AST Parse Error: {e}]"
        return manifest

    manifest.docstring = ast.get_docstring(tree) or ""

    deps = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                deps.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                deps.add(node.module.split(".")[0])

    manifest.dependencies = sorted(list(deps))

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            c_doc = ast.get_docstring(node) or ""
            manifest.classes.append(
                SymbolContract(
                    name=node.name,
                    kind="class",
                    docstring=c_doc.strip(),
                    line_number=node.lineno,
                    decorators=[ast.unparse(d) for d in node.decorator_list if hasattr(ast, "unparse")]
                )
            )
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    m_doc = ast.get_docstring(item) or ""
                    sig = ""
                    if hasattr(ast, "unparse"):
                        args_str = ast.unparse(item.args)
                        ret_str = f" -> {ast.unparse(item.returns)}" if item.returns else ""
                        sig = f"{item.name}({args_str}){ret_str}"
                    manifest.functions.append(
                        SymbolContract(
                            name=f"{node.name}.{item.name}",
                            kind="method",
                            docstring=m_doc.strip(),
                            signature=sig,
                            line_number=item.lineno
                        )
                    )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            f_doc = ast.get_docstring(node) or ""
            sig = ""
            if hasattr(ast, "unparse"):
                args_str = ast.unparse(node.args)
                ret_str = f" -> {ast.unparse(node.returns)}" if node.returns else ""
                sig = f"{node.name}({args_str}){ret_str}"
            manifest.functions.append(
                SymbolContract(
                    name=node.name,
                    kind="function",
                    docstring=f_doc.strip(),
                    signature=sig,
                    line_number=node.lineno
                )
            )

    return manifest


def link_adrs_and_traps(manifest: ModuleManifest, root: Path = ROOT_DIR) -> ModuleManifest:
    """Discovers related ADRs, Traps, and Specs for this module."""
    mod_stem = manifest.module_name.lower()
    adr_dir = root / ".teamzero" / "memory" / "adr"
    traps_dir = root / ".teamzero" / "memory" / "traps"
    specs_dir = root / ".teamzero" / "memory" / "specs"

    # Scan ADRs
    citations = []
    if adr_dir.is_dir():
        for adr in adr_dir.glob("*.md"):
            try:
                txt = adr.read_text(encoding="utf-8").lower()
                if mod_stem in txt or manifest.file_path.lower() in txt:
                    citations.append(adr.name)
            except Exception:
                pass
    manifest.adr_citations = sorted(citations)

    # Check Traps
    if traps_dir.is_dir():
        trap_file = traps_dir / f"{mod_stem}.md"
        manifest.has_traps = trap_file.exists()

    # Check Specs
    if specs_dir.is_dir():
        spec_file = specs_dir / f"{mod_stem}_spec.json"
        manifest.has_spec = spec_file.exists()

    return manifest


def generate_living_map_card(manifest: ModuleManifest, root: Path = ROOT_DIR) -> str:
    """Generates a concise Living Module Map card (<400 tokens) adhering to ADR-002."""
    map_dir = root / ".teamzero" / "memory" / "map"
    map_dir.mkdir(parents=True, exist_ok=True)
    card_path = map_dir / f"{manifest.module_name}.md"

    doc_excerpt = manifest.docstring.strip() if manifest.docstring else "No module docstring registered."
    first_paragraph = doc_excerpt.split("\n\n")[0] if "\n\n" in doc_excerpt else doc_excerpt

    classes_str = "\n".join(f"- `{c.name}`: {c.docstring.splitlines()[0] if c.docstring else 'Class contract'}" for c in manifest.classes[:6]) or "None"
    funcs_str = "\n".join(f"- `{f.signature or f.name}`" for f in manifest.functions[:10]) or "None"
    deps_str = ", ".join(f"`{d}`" for d in manifest.dependencies[:8]) or "None"
    adrs_str = ", ".join(f"[{a}](../adr/{a})" for a in manifest.adr_citations) or "ADR-000-genesis.md"

    trap_note = f"[View Anti-Patterns & Traps](../traps/{manifest.module_name}.md)" if manifest.has_traps else "No traps registered"
    spec_note = f"[Executable Spec](../specs/{manifest.module_name}_spec.json)" if manifest.has_spec else "Implicit or Constitution-governed"

    content = f"""# Living Architecture Map: {manifest.module_name}

## 1. Intent & Purpose (The "Why")
{first_paragraph}

## 2. Public Interfaces & Contracts (The "What")
### Classes
{classes_str}

### Key Functions
{funcs_str}

## 3. Structural Graph
- **Dependencies**: {deps_str}
- **Governing ADRs**: {adrs_str}
- **Known Traps**: {trap_note}
- **Executable Contract**: {spec_note}

---
*Generated by TeamZero Living Code Wiki Engine. Synchronized on {manifest.last_updated}.*
"""
    card_path.write_text(content, encoding="utf-8")
    return content


def generate_llms_txt(manifests: List[ModuleManifest], root: Path = ROOT_DIR) -> str:
    """Compiles a flat-file .llms.txt index optimized for AI coding assistants."""
    llms_path = root / ".llms.txt"

    adr_dir = root / ".teamzero" / "memory" / "adr"
    adrs = []
    if adr_dir.is_dir():
        for a in sorted(adr_dir.glob("*.md")):
            # extract first line or title
            title = a.name
            try:
                first_line = a.read_text(encoding="utf-8").splitlines()[0]
                if first_line.startswith("#"):
                    title = first_line.lstrip("# ").strip()
            except Exception:
                pass
            adrs.append(f"- [{title}](.teamzero/memory/adr/{a.name})")

    adrs_summary = "\n".join(adrs) if adrs else "- ADR-000: Genesis"

    mod_lines = []
    for m in manifests:
        summary = m.docstring.splitlines()[0] if m.docstring else "System module"
        mod_lines.append(f"- **{m.module_name}** (`{Path(m.file_path).name}`): {summary}")

    mods_summary = "\n".join(mod_lines)

    content = f"""# TeamZero Codebase Context & Living Index
> Flat-file living architecture index for autonomous agents and solo founders.
> Designed for rapid LLM onboarding without whole-repo context ingestion.

## Core Invariants
1. **INV-01 (Generator Never Verifies)**: Author agent and reviewer/QA execute on distinct prompts/models.
2. **INV-02 (QA Sees The Spec, Never The Diff)**: Verification authored against specs, preventing confirmation bias.
3. **INV-03 (Done Is Computed, Never Asserted)**: Status is validated by automated merge gauntlets and HMAC receipts.
4. **INV-04 (Zero Secrets & Protected Constitution)**: Sandboxes hold no keys; constitution cannot be agent-modified.
5. **INV-05 (Failure Has A Price)**: Breaker catches deduct token budgets and decay agent trust scores.

## Architecture & Submodules
{mods_summary}

## Architecture Decision Records (The "Why")
{adrs_summary}

## Developer & Agent Runbooks
- [Onboarding Runbook](.teamzero/runbooks/onboarding.md)
- [Disaster Recovery](.teamzero/runbooks/disaster_recovery.md)
- [PR Review Playbook](.teamzero/runbooks/pr_review_playbook.md)

## Navigation Guidelines
- Query memory via Model Context Protocol: `teamzero_query_memory` or `teamzero_get_spec`.
- Inspect living map cards under `.teamzero/memory/map/{'{module}'}.md` before modifying submodules.
- Execute the merge gauntlet via `teamzero_run_gauntlet` before submitting candidate commits.
"""
    llms_path.write_text(content, encoding="utf-8")
    return content


def generate_wiki_json(manifests: List[ModuleManifest], root: Path = ROOT_DIR) -> Dict[str, Any]:
    """Compiles machine-readable wiki.json sitemap."""
    wiki_json_path = root / ".teamzero" / "wiki.json"
    wiki_json_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": "1.0",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_modules": len(manifests),
        "modules": {m.module_name: m.to_dict() for m in manifests}
    }

    wiki_json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def ensure_runbooks(root: Path = ROOT_DIR):
    """Generates standard operational runbooks in .teamzero/runbooks/."""
    runbook_dir = root / ".teamzero" / "runbooks"
    runbook_dir.mkdir(parents=True, exist_ok=True)

    onboarding = """# Onboarding Runbook: Developer & Agent Workflow

## 1. Quickstart Commands
- **Environment Doctor**: `python -m teamzero.cli doctor`
- **Living Status**: `python -m teamzero.cli status`
- **Active Task Navigator**: `python -m teamzero.cli task next`
- **Design Thinking Ideator**: `python -m teamzero.cli ideate`
- **Living Code Wiki**: `python -m teamzero.cli docs build`

## 2. Invariants & Rules
Every change must be validated against the Quality Constitution (`.teamzero/constitution.yaml`).
Autonomous agents cannot self-merge; merge requires HMAC-signed gauntlet receipts.

## 3. Local Environment Quirks
- On Windows PowerShell, verify execution policy or invoke via `python -m teamzero.cli`.
- MCP server runs via `python -m teamzero.mcp_server`.
"""

    disaster = """# Disaster Recovery Runbook

## 1. Context Poisoning or Corrupted ADRs
- If an agent or untrusted client attempts to inject prompt overrides into memory:
  1. Inspect red-team findings: `python -m teamzero.cli health`.
  2. The hash-chained receipts ledger (`.teamzero/ledger/receipts.jsonl`) verifies genesis integrity.
  3. Revert corrupted `.teamzero/memory/` files using `git checkout origin/main -- .teamzero/memory/`.

## 2. Compromised Mint Authority
- Rotate the local key: delete `.teamzero/.mintkey` and set a new `TZ_SERVER_SECRET` environment variable.
- Re-run `python -m teamzero.init_project doctor` to verify ledger HMAC chain.
"""

    pr_playbook = """# PR Review Playbook: Human Founder & QA Gate

## 1. Review Checklist
- [ ] Does the PR include tests authored strictly against specifications?
- [ ] Are relevant Living Map cards (`.teamzero/memory/map/*.md`) updated?
- [ ] If architectural trade-offs were made, is there a new ADR in `.teamzero/memory/adr/`?
- [ ] Did the automated merge gauntlet pass with 0 critical breaker findings?
"""

    (runbook_dir / "onboarding.md").write_text(onboarding, encoding="utf-8")
    (runbook_dir / "disaster_recovery.md").write_text(disaster, encoding="utf-8")
    (runbook_dir / "pr_review_playbook.md").write_text(pr_playbook, encoding="utf-8")


def build_living_wiki(root: Path = ROOT_DIR) -> Dict[str, Any]:
    """Orchestrates end-to-end AST parsing, Living Map cards, .llms.txt, and wiki.json."""
    ensure_runbooks(root)

    src_dir = root / "teamzero"
    manifests: List[ModuleManifest] = []

    if src_dir.is_dir():
        for py_file in sorted(src_dir.glob("*.py")):
            if py_file.name.startswith("__"):
                continue
            manifest = extract_module_symbols(py_file)
            manifest = link_adrs_and_traps(manifest, root=root)
            generate_living_map_card(manifest, root=root)
            manifests.append(manifest)

    llms_content = generate_llms_txt(manifests, root=root)
    wiki_data = generate_wiki_json(manifests, root=root)

    return {
        "status": "BUILT",
        "total_modules": len(manifests),
        "llms_txt_bytes": len(llms_content),
        "modules": [m.module_name for m in manifests]
    }


def prune_and_validate_wiki(root: Path = ROOT_DIR, fix: bool = False) -> Dict[str, Any]:
    """Bonsai Tree Pruner & Broken Hyperlink Validator."""
    map_dir = root / ".teamzero" / "memory" / "map"
    src_dir = root / "teamzero"

    broken_links: List[Dict[str, str]] = []
    stale_cards: List[str] = []
    pruned_cards: List[str] = []

    # 1. Detect stale map cards (card exists but source python file was deleted)
    if map_dir.is_dir():
        for card in map_dir.glob("*.md"):
            mod_name = card.stem
            # Check if matching source file exists
            source_exists = (src_dir / f"{mod_name}.py").exists() if src_dir.is_dir() else False
            if not source_exists and mod_name != "refund":  # keep refund as reference fixture
                stale_cards.append(card.name)
                if fix:
                    card.unlink(missing_ok=True)
                    pruned_cards.append(card.name)

    # 2. Check internal markdown links across all memory and doc files
    scan_dirs = [root / ".teamzero" / "memory", root / ".teamzero" / "runbooks"]
    for sdir in scan_dirs:
        if not sdir.is_dir():
            continue
        for md_file in sdir.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
                for label, target in links:
                    if target.startswith("http://") or target.startswith("https://") or target.startswith("#"):
                        continue
                    # Clean anchor
                    file_target = target.split("#")[0]
                    if not file_target:
                        continue
                    resolved = (md_file.parent / file_target).resolve()
                    if not resolved.exists():
                        broken_links.append({
                            "source_file": str(md_file.relative_to(root)),
                            "label": label,
                            "target": target
                        })
            except Exception:
                pass

    return {
        "status": "HEALTHY" if not broken_links and not stale_cards else "ATTENTION_NEEDED",
        "stale_cards_detected": stale_cards,
        "cards_pruned": pruned_cards,
        "broken_links_count": len(broken_links),
        "broken_links": broken_links
    }


def check_docs_drift(
    root: Path = ROOT_DIR,
    changed_files: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Docs-as-Code PR Gatekeeper: Flags when functional code changes without matching doc updates."""
    if changed_files is None:
        try:
            res = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=str(root))
            changed_files = []
            for line in res.stdout.splitlines():
                if len(line) > 3:
                    # Clean filename (handle renames: old -> new)
                    f_name = line[3:].strip()
                    if " -> " in f_name:
                        f_name = f_name.split(" -> ")[1].strip()
                    changed_files.append(f_name.replace("\\", "/"))
        except Exception:
            changed_files = []

    code_files = [f for f in changed_files if f.endswith(".py") and not f.startswith("tests/")]
    doc_files = [f for f in changed_files if f.endswith(".md") or ".teamzero/memory/" in f or f == ".llms.txt" or "runbooks" in f]

    # If code changed, docs must change or a Living Map card must be touched
    has_drift = len(code_files) > 0 and len(doc_files) == 0

    return {
        "passed": not has_drift,
        "drift_detected": has_drift,
        "code_files_changed": code_files,
        "doc_files_changed": doc_files,
        "recommendation": (
            "Documentation is synchronized with code."
            if not has_drift
            else "Code modified without updating documentation. Update .teamzero/memory/map/, an ADR, or run 'tz docs build'."
        )
    }
