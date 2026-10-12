"""Smart AST-Aware, Symbol-Indexed, and Reference-Compressed File Reader.

Implements token-slashing patterns inspired by AST-symbol extractors, SQZ reference compression,
and Spotify Portal-style size guardrails:
1. AST-Aware Symbol Extraction: `read_symbol(file, symbol)` extracts only the target function/class.
2. Reference & Token Compression (SQZ pattern): tracks read hashes; subsequent reads return lightweight ref IDs.
3. Progressive Disclosure (Outline First): `inspect_outline(file)` returns a 15-25 line skeleton/TOC.
4. Large File Guardrails: blocks raw dumps of files > 350 lines unless force=True.
5. Semantic Log Filter: strips progress bars, repeat timestamps, and noise from terminal dumps.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from teamzero.config import ROOT_DIR, CACHE_DIR


# In-memory session reference cache: client_id -> set of ref_ids
_SQZ_SESSION_CACHE: Dict[str, Set[str]] = {}


def _get_cache_file() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / "sqz_refs.json"


def _record_ref(client_id: str, ref_id: str):
    _SQZ_SESSION_CACHE.setdefault(client_id, set()).add(ref_id)
    try:
        c_file = _get_cache_file()
        data = {}
        if c_file.exists():
            try:
                data = json.loads(c_file.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        client_set = set(data.get(client_id, []))
        client_set.add(ref_id)
        data[client_id] = sorted(list(client_set))
        c_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def _is_ref_cached(client_id: str, ref_id: str) -> bool:
    if ref_id in _SQZ_SESSION_CACHE.get(client_id, set()):
        return True
    try:
        c_file = _get_cache_file()
        if c_file.exists():
            data = json.loads(c_file.read_text(encoding="utf-8"))
            return ref_id in data.get(client_id, [])
    except Exception:
        pass
    return False


def clear_session_cache(client_id: Optional[str] = None):
    """Clears SQZ session reference cache."""
    global _SQZ_SESSION_CACHE
    if client_id:
        _SQZ_SESSION_CACHE.pop(client_id, None)
    else:
        _SQZ_SESSION_CACHE.clear()
    c_file = _get_cache_file()
    if c_file.exists():
        try:
            if client_id:
                data = json.loads(c_file.read_text(encoding="utf-8"))
                data.pop(client_id, None)
                c_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            else:
                c_file.unlink(missing_ok=True)
        except Exception:
            pass


@dataclass
class SymbolItem:
    name: str
    kind: str  # class | method | function | section
    start_line: int
    end_line: int
    signature: str = ""
    docstring: str = ""
    parent: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _resolve_file_path(target_path: Path | str, root: Path = ROOT_DIR) -> Path:
    p = Path(target_path)
    if not p.is_absolute():
        p = (root / p).resolve()
    return p


def inspect_outline(target_path: Path | str, root: Path = ROOT_DIR) -> Dict[str, Any]:
    """Inspects file structure and returns a compact AST-driven skeleton (Table of Contents)."""
    p = _resolve_file_path(target_path, root)
    if not p.exists():
        return {"error": f"File '{target_path}' not found.", "file": str(target_path)}

    rel_name = str(p.relative_to(root)) if root in p.parents or p == root else p.name
    content = p.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    total_lines = len(lines)
    size_bytes = p.stat().st_size

    symbols: List[SymbolItem] = []

    # 1. Python AST parsing
    if p.suffix == ".py":
        try:
            tree = ast.parse(content, filename=str(p))
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    c_doc = ast.get_docstring(node) or ""
                    c_summary = c_doc.splitlines()[0] if c_doc else ""
                    end_ln = getattr(node, "end_lineno", node.lineno)
                    symbols.append(
                        SymbolItem(
                            name=node.name,
                            kind="class",
                            start_line=node.lineno,
                            end_line=end_ln,
                            docstring=c_summary
                        )
                    )
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            m_doc = ast.get_docstring(item) or ""
                            m_summary = m_doc.splitlines()[0] if m_doc else ""
                            m_end = getattr(item, "end_lineno", item.lineno)
                            sig = ""
                            if hasattr(ast, "unparse"):
                                args_str = ast.unparse(item.args)
                                ret_str = f" -> {ast.unparse(item.returns)}" if item.returns else ""
                                sig = f"{item.name}({args_str}){ret_str}"
                            symbols.append(
                                SymbolItem(
                                    name=f"{node.name}.{item.name}",
                                    kind="method",
                                    start_line=item.lineno,
                                    end_line=m_end,
                                    signature=sig,
                                    docstring=m_summary,
                                    parent=node.name
                                )
                            )
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    f_doc = ast.get_docstring(node) or ""
                    f_summary = f_doc.splitlines()[0] if f_doc else ""
                    f_end = getattr(node, "end_lineno", node.lineno)
                    sig = ""
                    if hasattr(ast, "unparse"):
                        args_str = ast.unparse(node.args)
                        ret_str = f" -> {ast.unparse(node.returns)}" if node.returns else ""
                        sig = f"{node.name}({args_str}){ret_str}"
                    symbols.append(
                        SymbolItem(
                            name=node.name,
                            kind="function",
                            start_line=node.lineno,
                            end_line=f_end,
                            signature=sig,
                            docstring=f_summary
                        )
                    )
        except Exception:
            pass

    # 2. Fallback / Regex-based scanning for TS/JS/Rust/Go/Markdown
    if not symbols:
        for idx, line in enumerate(lines, 1):
            line_s = line.strip()
            # Markdown Headings
            if line_s.startswith("#"):
                symbols.append(SymbolItem(name=line_s, kind="section", start_line=idx, end_line=idx))
            # JS/TS/Go/Rust functions & classes
            elif re.search(r"\b(?:export\s+)?(?:class|interface|type)\s+([A-Za-z0-9_]+)", line_s):
                m = re.search(r"\b(?:export\s+)?(?:class|interface|type)\s+([A-Za-z0-9_]+)", line_s)
                symbols.append(SymbolItem(name=m.group(1), kind="class", start_line=idx, end_line=idx))
            elif re.search(r"\b(?:function|fn|func|def)\s+([A-Za-z0-9_]+)\s*\(", line_s):
                m = re.search(r"\b(?:function|fn|func|def)\s+([A-Za-z0-9_]+)\s*\(", line_s)
                symbols.append(SymbolItem(name=m.group(1), kind="function", start_line=idx, end_line=idx))

    # Build compact text outline
    outline_lines = [f"Outline of `{rel_name}` ({total_lines} lines, {size_bytes} bytes):"]
    if not symbols:
        outline_lines.append("  (No top-level class or function symbols detected)")
    for s in symbols:
        sig_str = f": {s.signature}" if s.signature else ""
        doc_str = f" - {s.docstring}" if s.docstring else ""
        indent = "    " if s.kind == "method" else "  "
        badge = f"[{s.kind.upper()[:4]}]"
        outline_lines.append(f"{indent}{badge} L{s.start_line:03d}-{s.end_line:03d} {s.name}{sig_str}{doc_str}")

    return {
        "file": rel_name,
        "total_lines": total_lines,
        "size_bytes": size_bytes,
        "symbol_count": len(symbols),
        "symbols": [s.to_dict() for s in symbols],
        "outline_text": "\n".join(outline_lines)
    }


def read_symbol(
    target_path: Path | str,
    symbol_name: str,
    client_id: str = "anon",
    force: bool = False,
    root: Path = ROOT_DIR
) -> Dict[str, Any]:
    """Extracts only the requested function, class, or method body via AST.

    Implements the SQZ token-compression pattern:
    If the target block has already been read in this session and remains unchanged,
    it returns a compact reference token instead of re-injecting raw source code.
    """
    p = _resolve_file_path(target_path, root)
    if not p.exists():
        return {"error": f"File '{target_path}' not found.", "file": str(target_path)}

    rel_name = str(p.relative_to(root)) if root in p.parents or p == root else p.name
    content = p.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()

    outline = inspect_outline(target_path, root)
    symbols = outline.get("symbols", [])

    # Match target symbol
    target_sym = None
    target_clean = symbol_name.strip().lower()
    for s in symbols:
        s_name = s["name"].lower()
        if s_name == target_clean or s_name.endswith(f".{target_clean}") or s["name"].split(".")[-1].lower() == target_clean:
            target_sym = s
            break

    if not target_sym:
        avail = [s["name"] for s in symbols]
        return {
            "error": f"Symbol '{symbol_name}' not found in {rel_name}.",
            "available_symbols": avail[:15],
            "file": rel_name
        }

    start = target_sym["start_line"]
    end = target_sym["end_line"]
    extracted_lines = lines[start - 1 : end]
    code_block = "\n".join(extracted_lines)

    # Compute SQZ fingerprint
    chunk_hash = hashlib.sha256(code_block.encode("utf-8")).hexdigest()
    ref_id = f"SQZ:{chunk_hash[:12]}"

    if not force and _is_ref_cached(client_id, ref_id):
        return {
            "status": "SQZ_CACHED",
            "ref_id": ref_id,
            "file": rel_name,
            "symbol": target_sym["name"],
            "lines": f"L{start}-L{end}",
            "line_count": len(extracted_lines),
            "message": (
                f"[SQZ-CACHED: ref_id='{ref_id}', symbol='{target_sym['name']}', "
                f"lines={len(extracted_lines)}, status='UNCHANGED']. "
                f"Block already in session context. Pass force=True to re-read raw code."
            )
        }

    # Record in cache
    _record_ref(client_id, ref_id)

    return {
        "status": "READ",
        "ref_id": ref_id,
        "file": rel_name,
        "symbol": target_sym["name"],
        "kind": target_sym["kind"],
        "lines": f"L{start}-L{end}",
        "line_count": len(extracted_lines),
        "signature": target_sym.get("signature", ""),
        "docstring": target_sym.get("docstring", ""),
        "content": code_block
    }


def read_compressed_file(
    target_path: Path | str,
    max_lines: int = 350,
    force: bool = False,
    client_id: str = "anon",
    root: Path = ROOT_DIR
) -> Dict[str, Any]:
    """Reads a file with progressive disclosure guardrails and SQZ reference compression.

    If file exceeds `max_lines` (default 350) and force=False, returns the compact outline
    to prevent prompt explosion.
    """
    p = _resolve_file_path(target_path, root)
    if not p.exists():
        return {"error": f"File '{target_path}' not found.", "file": str(target_path)}

    rel_name = str(p.relative_to(root)) if root in p.parents or p == root else p.name
    content = p.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    total_lines = len(lines)

    # Progressive disclosure guardrail
    if total_lines > max_lines and not force:
        outline = inspect_outline(target_path, root)
        return {
            "guardrail_triggered": True,
            "file": rel_name,
            "total_lines": total_lines,
            "limit": max_lines,
            "message": (
                f"GUARDRAIL TRIGGERED: `{rel_name}` has {total_lines} lines (> {max_lines} limit). "
                f"To conserve context tokens, a compact outline is provided below. "
                f"Call read_symbol(file='{rel_name}', symbol='<name>') for specific functions, "
                f"or pass force=True to dump raw file."
            ),
            "outline": outline["outline_text"]
        }

    # SQZ token compression check
    file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    ref_id = f"SQZ:{file_hash[:12]}"

    if not force and _is_ref_cached(client_id, ref_id):
        return {
            "status": "SQZ_CACHED",
            "ref_id": ref_id,
            "file": rel_name,
            "total_lines": total_lines,
            "message": (
                f"[SQZ-CACHED: ref_id='{ref_id}', file='{rel_name}', "
                f"lines={total_lines}, status='UNCHANGED']. "
                f"File content already present in context history. Pass force=True to re-read."
            )
        }

    _record_ref(client_id, ref_id)

    return {
        "status": "READ",
        "ref_id": ref_id,
        "file": rel_name,
        "total_lines": total_lines,
        "content": content
    }


def filter_terminal_output(raw_output: str, max_lines: int = 60) -> str:
    """Strips terminal noise, progress bars, and repeat timestamps.

    Preserves failures, tracebacks, diff chunks, and final metrics.
    """
    if not raw_output:
        return ""

    # Strip ANSI escape sequences
    clean = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", raw_output)

    # Strip progress bars (e.g., [=====>   ] or 100%|#####|)
    clean = re.sub(r"\[[#=\- ]{5,}\]", "", clean)
    clean = re.sub(r"\b\d+%\b\s*\|[#=\- ]+\|\s*", "", clean)

    lines = clean.splitlines()
    filtered: List[str] = []

    high_value_patterns = [
        re.compile(r"Traceback \(most recent call last\):", re.I),
        re.compile(r"^\s*File\s+\".*\",\s+line\s+\d+", re.I),
        re.compile(r"^\s*(?:AssertionError|ValueError|TypeError|KeyError|AttributeError|Exception):", re.I),
        re.compile(r"^\s*(?:FAILED|PASSED|ERROR|FAIL|PASS)\b", re.I),
        re.compile(r"^[+-]{3}\s+", re.I),
        re.compile(r"^@@\s+-\d+,\d+\s+\+\d+,\d+\s+@@", re.I),
        re.compile(r"^\s*[+-]\s+", re.I),
        re.compile(r"(?:tests passed|tests failed|passed in|failed in)", re.I),
    ]

    for line in lines:
        line_s = line.strip()
        if not line_s:
            continue
        # Strip repeated leading timestamps: 2026-10-12 20:20:01
        line_s = re.sub(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z)?\s*", "", line_s)
        # Skip pure separator bars of > 20 repeat chars
        if re.match(r"^([=\-_.*#])\1{20,}$", line_s):
            continue
        filtered.append(line_s)

    if len(filtered) <= max_lines:
        return "\n".join(filtered)

    # If exceeding max_lines, prioritize head, high-value lines, and tail
    head = filtered[:10]
    tail = filtered[-25:]
    middle = filtered[10:-25]

    high_value_middle = [
        l for l in middle
        if any(p.search(l) for p in high_value_patterns)
    ]

    result = head + ["... [Noise & progress output truncated] ..."] + high_value_middle[:20] + tail
    return "\n".join(result[:max_lines])
