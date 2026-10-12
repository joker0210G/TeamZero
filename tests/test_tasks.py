"""Unit tests for TeamZero Task Decomposition & Dependency Engine."""

from pathlib import Path
import pytest

from teamzero.tasks import TaskRegistry, MicroTask

SAMPLE_PRD = """# Feature: Instant Micro-Refund
## Acceptance Criteria
- [ ] Initialize domain interface and input validation
- [ ] Implement core calculation logic
- [ ] Ensure non-negative refund invariant is strictly enforced
"""


def test_task_registry_crud(tmp_path):
    reg_file = tmp_path / "tasks.json"
    reg = TaskRegistry(registry_file=reg_file)

    t1 = MicroTask(id="TASK-01", title="Task 1", description="First task", complexity=3)
    t2 = MicroTask(id="TASK-02", title="Task 2", description="Second task", dependencies=["TASK-01"], complexity=5)

    reg.save_tasks([t1, t2])
    loaded = reg.load_tasks()
    assert len(loaded) == 2
    assert loaded[0].id == "TASK-01"

    # Navigation: Next task should be TASK-01 (TASK-02 is blocked)
    nxt = reg.get_next_task()
    assert nxt is not None
    assert nxt.id == "TASK-01"

    # Mark TASK-01 as GAUNTLET_PASS
    reg.update_status("TASK-01", "GAUNTLET_PASS")
    nxt2 = reg.get_next_task()
    assert nxt2 is not None
    assert nxt2.id == "TASK-02"


def test_decompose_prd(tmp_path):
    reg_file = tmp_path / "tasks.json"
    reg = TaskRegistry(registry_file=reg_file)

    tasks = reg.decompose_prd(SAMPLE_PRD, feature_prefix="REFUND")
    assert len(tasks) == 3
    assert tasks[0].id == "REFUND-01"
    assert tasks[1].dependencies == ["REFUND-01"]
    assert tasks[2].dependencies == ["REFUND-02"]


def test_expand_task(tmp_path):
    reg_file = tmp_path / "tasks.json"
    reg = TaskRegistry(registry_file=reg_file)

    t1 = MicroTask(id="TASK-CORE", title="Core Task", description="Big task", complexity=7)
    reg.save_tasks([t1])

    subs = reg.expand_task("TASK-CORE", ["Subpart A", "Subpart B"])
    assert len(subs) == 2
    assert subs[0].id == "TASK-CORE.1"
    assert subs[1].dependencies == ["TASK-CORE.1"]

    parent = reg.get_task("TASK-CORE")
    assert "TASK-CORE.1" in parent.subtasks


def test_subtask_crud_and_fix_dependencies(tmp_path):
    reg_file = tmp_path / "tasks.json"
    reg = TaskRegistry(registry_file=reg_file)

    t1 = MicroTask(id="TASK-P", title="Parent Task", description="Main task", complexity=5)
    reg.save_tasks([t1])

    # Add subtask
    sub = reg.add_subtask("TASK-P", "Child Step 1")
    assert sub is not None
    assert sub.id == "TASK-P.1"
    assert "TASK-P.1" in reg.get_task("TASK-P").subtasks

    # Add dependency pointing to a non-existent task
    reg.add_dependency("TASK-P", "NON_EXISTENT_999")
    val = reg.validate_dependencies()
    assert not val["valid"]
    assert "NON_EXISTENT_999" in val["missing_dependencies"]["TASK-P"]

    # Auto fix dependencies
    fix_res = reg.fix_dependencies()
    assert fix_res["fixed_count"] == 1
    assert "NON_EXISTENT_999" in fix_res["removed_dangling_dependencies"]["TASK-P"]
    assert reg.validate_dependencies()["valid"]

    # Remove subtask
    ok = reg.remove_subtask("TASK-P", "TASK-P.1")
    assert ok
    assert "TASK-P.1" not in reg.get_task("TASK-P").subtasks


def test_tool_loading_modes():
    import os
    import subprocess
    import sys

    # Core mode should load 7 tools
    env_core = dict(os.environ, TEAMZERO_TOOLS="core")
    out_core = subprocess.check_output(
        [sys.executable, "-c", "import teamzero.mcp_server as s; print(len(s.mcp._tool_manager._tools))"],
        env=env_core, text=True
    ).strip()
    assert int(out_core) == 7

    # Standard mode should load 22 tools
    env_std = dict(os.environ, TEAMZERO_TOOLS="standard")
    out_std = subprocess.check_output(
        [sys.executable, "-c", "import teamzero.mcp_server as s; print(len(s.mcp._tool_manager._tools))"],
        env=env_std, text=True
    ).strip()
    assert int(out_std) == 22

    # Custom selection
    env_custom = dict(os.environ, TEAMZERO_TOOLS="get_tasks,run_gauntlet")
    out_custom = subprocess.check_output(
        [sys.executable, "-c", "import teamzero.mcp_server as s; print(len(s.mcp._tool_manager._tools))"],
        env=env_custom, text=True
    ).strip()
    assert int(out_custom) == 2

