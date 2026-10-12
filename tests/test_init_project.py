import json
import os
import shutil
import tempfile
from pathlib import Path
import pytest
import yaml

from teamzero.init_project import init_project
from teamzero.config import find_project_root


def test_init_project_creates_structure():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "test_app"
        org_dir = init_project(target, name="TestApp")

        assert org_dir.exists()
        assert (org_dir / "constitution.yaml").exists()
        assert (org_dir / ".mintkey").exists()
        assert (org_dir / ".gitignore").exists()
        assert (org_dir / "providers.yaml").exists()
        assert (org_dir / "health.json").exists()

        # Check subdirectories
        for subdir in [
            "memory/specs",
            "memory/adr",
            "memory/map",
            "memory/traps",
            "memory/evidence",
            "memory/tasks",
            "redteam/campaigns",
            "redteam/findings",
            "inbox/asks",
            "inbox/decisions",
            "ledger",
            "journal",
            "triggers",
        ]:
            assert (org_dir / subdir).is_dir(), f"Missing directory: {subdir}"

        # Check constitution contents
        const_data = yaml.safe_load((org_dir / "constitution.yaml").read_text(encoding="utf-8"))
        assert const_data["organization"]["name"] == "TestApp"
        assert const_data["organization"]["version"] == "0.1.0-alpha.3"
        assert len(const_data["invariants"]) == 5

        # Check ledgers exist
        assert (org_dir / "ledger" / "trust.jsonl").exists()
        assert (org_dir / "ledger" / "payroll.jsonl").exists()
        assert (org_dir / "ledger" / "receipts.jsonl").exists()


def test_init_project_idempotent():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "idempotent_app"
        org_dir1 = init_project(target, name="AppOne")
        mintkey_1 = (org_dir1 / ".mintkey").read_text(encoding="utf-8")

        # Second init should not overwrite mintkey or constitution
        org_dir2 = init_project(target, name="AppOne")
        mintkey_2 = (org_dir2 / ".mintkey").read_text(encoding="utf-8")

        assert mintkey_1 == mintkey_2


def test_find_project_root_env_override(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("TZ_PROJECT_DIR", tmpdir)
        root = find_project_root()
        assert root == Path(tmpdir).resolve()
