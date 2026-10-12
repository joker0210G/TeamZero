import json
import os
import shutil
import tempfile
from pathlib import Path
import pytest
import yaml

from teamzero.init_project import init_project, cmd_doctor, detect_profile
from teamzero.config import find_project_root


def test_init_project_creates_structure():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "test_app"
        target.mkdir()
        # Create marker to detect python profile
        (target / "pyproject.toml").write_text("[project]\nname='test_app'\n", encoding="utf-8")

        org_dir = init_project(target, name="TestApp")

        assert org_dir.exists()
        assert (org_dir / "constitution.yaml").exists()
        assert (org_dir / ".mintkey").exists()
        assert (target / ".gitignore").exists()
        assert (target / "antigravity_mcp.json").exists()
        assert (target / "claude_mcp.json").exists()
        assert (target / ".mcp.json").exists()
        assert (org_dir / "memory" / "adr" / "ADR-000-genesis.md").exists()

        # Check subdirectories
        for subdir in [
            "memory/specs",
            "memory/adr",
            "memory/map",
            "memory/traps",
            "redteam/campaigns",
            "redteam/findings",
            "inbox/asks",
            "inbox/decisions",
            "ledger",
        ]:
            assert (org_dir / subdir).is_dir(), f"Missing directory: {subdir}"

        # Check constitution contents
        const_data = yaml.safe_load((org_dir / "constitution.yaml").read_text(encoding="utf-8"))
        assert const_data["organization"]["name"] == "TestApp"
        assert const_data["organization"]["version"] == "0.1.0-alpha.3"
        assert const_data["organization"]["profile"] == "python"
        assert len(const_data["invariants"]) == 5

        # Check ledgers exist and have genesis events
        assert (org_dir / "ledger" / "trust.jsonl").exists()
        assert (org_dir / "ledger" / "payroll.jsonl").exists()
        receipts_file = org_dir / "ledger" / "receipts.jsonl"
        assert receipts_file.exists()
        lines = [json.loads(l) for l in receipts_file.read_text().splitlines() if l.strip()]
        assert len(lines) == 1
        assert lines[0]["event"] == "genesis"
        assert "receipt_hmac" in lines[0]

        # Verify doctor passes
        class _Args:
            project_root = str(target)
        assert cmd_doctor(_Args()) == 0


def test_detect_profiles():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir)
        assert detect_profile(p, "auto") == "generic"

        (p / "package.json").write_text("{}", encoding="utf-8")
        assert detect_profile(p, "auto") == "node"

        (p / "Cargo.toml").write_text("", encoding="utf-8")
        assert detect_profile(p, "auto") in ["node", "rust"]


def test_find_project_root_env_override(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("TZ_ROOT", tmpdir)
        root = find_project_root()
        assert root == Path(tmpdir).resolve()
