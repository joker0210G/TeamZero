"""Unit tests for Smart AST Reader, SQZ Reference Compression, and Log Filtering."""

from pathlib import Path
import pytest

from teamzero.smart_reader import (
    inspect_outline,
    read_symbol,
    read_compressed_file,
    filter_terminal_output,
    clear_session_cache
)


SAMPLE_PYTHON_CODE = '''"""Sample module for AST reader testing."""

class AccountManager:
    """Handles user accounts."""

    def __init__(self, owner: str):
        self.owner = owner

    def deposit(self, amount: float) -> bool:
        """Deposits funds into account."""
        if amount <= 0:
            return False
        return True

    def withdraw(self, amount: float) -> bool:
        """Withdraws funds if available."""
        return amount > 0


def transfer_funds(source: str, target: str, amount: float) -> bool:
    """Executes atomic fund transfer."""
    return amount > 0
'''


def test_inspect_outline(tmp_path):
    p = tmp_path / "accounts.py"
    p.write_text(SAMPLE_PYTHON_CODE, encoding="utf-8")

    res = inspect_outline(p, root=tmp_path)
    assert res["file"] == "accounts.py"
    assert res["symbol_count"] == 5
    names = [s["name"] for s in res["symbols"]]
    assert "AccountManager" in names
    assert "AccountManager.deposit" in names
    assert "transfer_funds" in names
    assert "Outline of `accounts.py`" in res["outline_text"]


def test_read_symbol_ast_and_sqz_caching(tmp_path):
    clear_session_cache("test_client")
    p = tmp_path / "accounts.py"
    p.write_text(SAMPLE_PYTHON_CODE, encoding="utf-8")

    # 1. First read -> returns full symbol slice
    res1 = read_symbol(p, "deposit", client_id="test_client", root=tmp_path)
    assert res1["status"] == "READ"
    assert "def deposit" in res1["content"]
    assert "Deposits funds into account." in res1["content"]
    ref_id = res1["ref_id"]

    # 2. Second read -> SQZ token compression kicks in
    res2 = read_symbol(p, "deposit", client_id="test_client", root=tmp_path)
    assert res2["status"] == "SQZ_CACHED"
    assert res2["ref_id"] == ref_id
    assert "status='UNCHANGED'" in res2["message"]
    assert "content" not in res2

    # 3. Read with force=True -> bypasses cache
    res3 = read_symbol(p, "deposit", client_id="test_client", force=True, root=tmp_path)
    assert res3["status"] == "READ"
    assert "def deposit" in res3["content"]


def test_large_file_guardrail(tmp_path):
    p = tmp_path / "big_module.py"
    # Create file with 400 lines
    lines = [f"# line {i}" for i in range(400)]
    p.write_text("\n".join(lines), encoding="utf-8")

    # Guardrail triggers without force
    res = read_compressed_file(p, max_lines=350, force=False, root=tmp_path)
    assert res["guardrail_triggered"]
    assert "GUARDRAIL TRIGGERED" in res["message"]
    assert "big_module.py" in res["file"]

    # Bypass guardrail with force=True
    res_forced = read_compressed_file(p, max_lines=350, force=True, root=tmp_path)
    assert not res_forced.get("guardrail_triggered", False)
    assert res_forced["status"] == "READ"
    assert len(res_forced["content"].splitlines()) == 400


def test_filter_terminal_output():
    raw_terminal = (
        "\x1b[32m2026-10-12 20:20:01 [INFO] Initializing tests\x1b[0m\n"
        "[====================] 100% | 50/50\n"
        "======================================================================\n"
        "Traceback (most recent call last):\n"
        "  File \"test_engine.py\", line 15, in test_failure\n"
        "    assert result == True\n"
        "AssertionError: assert False == True\n"
        "======================================================================\n"
        "FAILED tests/test_engine.py::test_failure - AssertionError\n"
        "1 failed, 49 passed in 1.20s\n"
    )

    clean = filter_terminal_output(raw_terminal)
    assert "\x1b" not in clean  # ANSI escape codes stripped
    assert "Traceback (most recent call last):" in clean
    assert "AssertionError: assert False == True" in clean
    assert "FAILED tests/test_engine.py::test_failure" in clean
    assert "1 failed, 49 passed in 1.20s" in clean
    assert "======================================================================" not in clean
