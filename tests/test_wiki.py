"""Unit tests for TeamZero Living Code Wiki & Docs-as-Code Engine."""

import json
from pathlib import Path
import pytest

from teamzero.wiki import (
    extract_module_symbols,
    link_adrs_and_traps,
    generate_living_map_card,
    generate_llms_txt,
    generate_wiki_json,
    prune_and_validate_wiki,
    check_docs_drift,
    build_living_wiki,
    ModuleManifest,
    SymbolContract
)


def test_extract_module_symbols(tmp_path):
    py_code = '''"""Sample test module for AST extraction."""

from typing import List, Optional

GLOBAL_LIMIT = 100

class Engine:
    """Core calculation engine."""
    def run(self, speed: int = 1) -> bool:
        """Runs the engine."""
        return speed > 0

def calculate_metric(val: float) -> float:
    """Calculates float metric."""
    return val * 2.0
'''
    py_file = tmp_path / "sample_mod.py"
    py_file.write_text(py_code, encoding="utf-8")

    manifest = extract_module_symbols(py_file)
    assert manifest.module_name == "sample_mod"
    assert manifest.docstring == "Sample test module for AST extraction."
    assert len(manifest.classes) == 1
    assert manifest.classes[0].name == "Engine"
    assert manifest.classes[0].docstring == "Core calculation engine."
    assert "Engine.run" in [f.name for f in manifest.functions]
    assert "calculate_metric" in [f.name for f in manifest.functions]
    assert "typing" in manifest.dependencies


def test_generate_living_map_card(tmp_path):
    manifest = ModuleManifest(
        module_name="demo_service",
        file_path=str(tmp_path / "demo_service.py"),
        docstring="Demo service for verifying living map generation.",
        classes=[SymbolContract(name="DemoClient", kind="class", docstring="Client for service")],
        functions=[SymbolContract(name="run_demo", kind="function", signature="run_demo() -> bool")],
        dependencies=["typing", "sys"],
        adr_citations=["ADR-001-verification.md"],
        has_traps=True,
        has_spec=False
    )

    card_text = generate_living_map_card(manifest, root=tmp_path)
    card_file = tmp_path / ".teamzero" / "memory" / "map" / "demo_service.md"
    assert card_file.exists()
    assert "# Living Architecture Map: demo_service" in card_text
    assert "DemoClient" in card_text
    assert "run_demo()" in card_text
    assert "ADR-001-verification.md" in card_text


def test_llms_txt_and_wiki_json(tmp_path):
    manifests = [
        ModuleManifest(
            module_name="auth",
            file_path=str(tmp_path / "auth.py"),
            docstring="Authentication and session tokens.",
            dependencies=["hashlib"]
        ),
        ModuleManifest(
            module_name="billing",
            file_path=str(tmp_path / "billing.py"),
            docstring="Billing and invoice management.",
            dependencies=["decimal"]
        )
    ]

    llms_txt = generate_llms_txt(manifests, root=tmp_path)
    assert "# TeamZero Codebase Context & Living Index" in llms_txt
    assert "INV-01 (Generator Never Verifies)" in llms_txt
    assert "auth" in llms_txt
    assert "billing" in llms_txt

    wiki_data = generate_wiki_json(manifests, root=tmp_path)
    assert wiki_data["total_modules"] == 2
    assert "auth" in wiki_data["modules"]
    assert (tmp_path / ".teamzero" / "wiki.json").exists()


def test_bonsai_pruning_and_hyperlinks(tmp_path):
    map_dir = tmp_path / ".teamzero" / "memory" / "map"
    src_dir = tmp_path / "teamzero"
    map_dir.mkdir(parents=True, exist_ok=True)
    src_dir.mkdir(parents=True, exist_ok=True)

    # Valid module card
    (src_dir / "valid_mod.py").write_text("# code", encoding="utf-8")
    (map_dir / "valid_mod.md").write_text("# valid card", encoding="utf-8")

    # Stale module card (source file does not exist)
    (map_dir / "old_deleted_mod.md").write_text("# stale card", encoding="utf-8")

    # Check without fix
    report = prune_and_validate_wiki(root=tmp_path, fix=False)
    assert "old_deleted_mod.md" in report["stale_cards_detected"]
    assert (map_dir / "old_deleted_mod.md").exists()

    # Check with fix (bonsai prune)
    report_fixed = prune_and_validate_wiki(root=tmp_path, fix=True)
    assert "old_deleted_mod.md" in report_fixed["cards_pruned"]
    assert not (map_dir / "old_deleted_mod.md").exists()


def test_docs_as_code_drift_check(tmp_path):
    # Case 1: Code changed, no docs changed -> Drift detected
    drift1 = check_docs_drift(root=tmp_path, changed_files=["teamzero/engine.py"])
    assert not drift1["passed"]
    assert drift1["drift_detected"]
    assert "engine.py" in drift1["code_files_changed"][0]

    # Case 2: Code changed, doc changed -> Synchronized
    drift2 = check_docs_drift(
        root=tmp_path,
        changed_files=["teamzero/engine.py", ".teamzero/memory/map/engine.md"]
    )
    assert drift2["passed"]
    assert not drift2["drift_detected"]

    # Case 3: Only docs changed -> Synchronized
    drift3 = check_docs_drift(root=tmp_path, changed_files=[".llms.txt", "README.md"])
    assert drift3["passed"]
    assert not drift3["drift_detected"]
