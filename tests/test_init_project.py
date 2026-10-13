import json
import tempfile
from pathlib import Path
import pytest
import yaml

from teamzero.init_project import init_project, cmd_doctor, detect_profile


def test_init_project_creates_structure_and_contract():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "test_app"
        target.mkdir()
        (target / "pyproject.toml").write_text("[project]\nname='test_app'\n", encoding="utf-8")

        org_dir = init_project(target, name="TestApp")

        assert org_dir.exists()
        assert (org_dir / "constitution.yaml").exists()
        assert (org_dir / "PROJECT_CONTRACT.md").exists()
        assert (org_dir / "runbooks" / "onboarding_session.md").exists()
        assert (org_dir / ".mintkey").exists()
        assert (target / ".gitignore").exists()
        assert (target / ".mcp.json").exists()
        assert (org_dir / "memory" / "adr" / "ADR-000-genesis.md").exists()

        # Check subdirectories
        for subdir in [
            "memory/specs",
            "memory/tasks",
            "memory/adr",
            "memory/map",
            "memory/traps",
            "inbox/asks",
            "inbox/decisions",
            "ledger",
            "runbooks",
        ]:
            assert (org_dir / subdir).is_dir(), f"Missing directory: {subdir}"

        # Check constitution contents for Praxist Zones of Autonomy
        const_data = yaml.safe_load((org_dir / "constitution.yaml").read_text(encoding="utf-8"))
        assert const_data["organization"]["name"] == "TestApp"
        assert "zones_of_autonomy" in const_data
        assert "green_autonomy_zone" in const_data["zones_of_autonomy"]
        assert "red_supervision_zone" in const_data["zones_of_autonomy"]
        assert len(const_data["invariants"]) == 5

        # Check ledgers have genesis receipts
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

        (p / "pyproject.toml").write_text("", encoding="utf-8")
        assert detect_profile(p, "auto") == "python"
