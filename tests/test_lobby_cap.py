"""Test ADR-003 Lobby Invariant and Tool Cap Enforcement."""

import pytest
from teamzero.mcp_server import mcp


def test_mcp_tool_cap_enforced():
    """ADR-003: A Lobby, Not A Vault.
    The MCP surface must not exceed 12 tools to prevent context rot.
    """
    tools = mcp._tool_manager._tools
    tool_names = list(tools.keys())
    
    assert len(tool_names) <= 12, f"Tool sprawl detected! Found {len(tool_names)} tools: {tool_names}"
    assert len(tool_names) == 10, f"Expected exactly 10 Dream Team tools, found {len(tool_names)}"


def test_forbidden_bypass_tools_do_not_exist():
    """Invariants INV-03 and INV-04:
    Done is computed, never asserted. Agents cannot merge or declare done.
    """
    tools = mcp._tool_manager._tools
    assert "teamzero_merge" not in tools, "Security breach: teamzero_merge must never exist as a tool!"
    assert "teamzero_set_done" not in tools, "Invariant violation: teamzero_set_done must never exist as a tool!"


def test_dream_team_tools_registered():
    """Ensure all 10 essential Dream Team tools are registered."""
    tools = mcp._tool_manager._tools
    expected = [
        "teamzero_query_memory",
        "teamzero_get_spec",
        "teamzero_run_gauntlet",
        "teamzero_submit_candidate",
        "teamzero_get_findings",
        "teamzero_file_decision",
        "teamzero_ask_founder",
        "teamzero_read_code",
        "teamzero_manage_tasks",
        "teamzero_verify_candidate",
    ]
    for name in expected:
        assert name in tools, f"Missing essential tool: {name}"
