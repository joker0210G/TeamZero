"""Hierarchical Task Decomposition & Dependency Engine for TeamZero.

Bridges human product requirement documents (PRD) and Design Thinking briefs
with granular, dependency-chained, and complexity-scored tasks for autonomous coding agents:
1. Decomposes PRDs/Asks into an ordered Directed Acyclic Graph (DAG) of microtasks.
2. Tracks dependencies, complexity scores (1-10), and execution states.
3. Provides native navigation: `get_next_task()`, complexity expansion, and progress tracking.
4. Enforces TeamZero Invariant 03: Done status is computed by verification, never claimed by agents.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from teamzero.config import TASKS_REGISTRY_FILE, ASKS_DIR


@dataclass
class MicroTask:
    id: str
    title: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    complexity: int = 3  # 1 (trivial) to 10 (architectural overhaul)
    status: str = "TODO"  # TODO | IN_PROGRESS | BLOCKED | GAUNTLET_PASS | VERIFIED
    target_files: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    assigned_agent: Optional[str] = None
    subtasks: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    updated_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MicroTask:
        return cls(
            id=data["id"],
            title=data.get("title", ""),
            description=data.get("description", ""),
            dependencies=data.get("dependencies", []),
            complexity=data.get("complexity", 3),
            status=data.get("status", "TODO"),
            target_files=data.get("target_files", []),
            acceptance_criteria=data.get("acceptance_criteria", []),
            assigned_agent=data.get("assigned_agent"),
            subtasks=data.get("subtasks", []),
            parent_id=data.get("parent_id"),
            updated_at=data.get("updated_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        )


class TaskRegistry:
    """Manages the centralized DAG task registry in .teamzero/tasks.json."""

    def __init__(self, registry_file: Optional[Path] = None):
        self.registry_file = registry_file or TASKS_REGISTRY_FILE

    def load_tasks(self) -> List[MicroTask]:
        if not self.registry_file.exists():
            return []
        try:
            data = json.loads(self.registry_file.read_text(encoding="utf-8"))
            return [MicroTask.from_dict(t) for t in data.get("tasks", [])]
        except Exception:
            return []

    def save_tasks(self, tasks: List[MicroTask]):
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": "1.0",
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_tasks": len(tasks),
            "tasks": [t.to_dict() for t in tasks]
        }
        self.registry_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get_task(self, task_id: str) -> Optional[MicroTask]:
        tasks = self.load_tasks()
        for t in tasks:
            if t.id.lower() == task_id.lower():
                return t
        return None

    def get_next_task(self) -> Optional[MicroTask]:
        """Returns the highest priority unblocked task ready for execution.
        A task is ready if its status is TODO and all dependencies are VERIFIED or GAUNTLET_PASS.
        """
        tasks = self.load_tasks()
        completed_ids = {t.id for t in tasks if t.status in ("VERIFIED", "GAUNTLET_PASS")}

        for t in tasks:
            if t.status == "TODO":
                # Check if all dependencies are satisfied
                if all(dep in completed_ids for dep in t.dependencies):
                    return t
        return None

    def update_status(self, task_id: str, new_status: str, agent_id: Optional[str] = None) -> Optional[MicroTask]:
        tasks = self.load_tasks()
        target = None
        for t in tasks:
            if t.id.lower() == task_id.lower():
                t.status = new_status.upper()
                t.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                if agent_id:
                    t.assigned_agent = agent_id
                target = t
                break
        if target:
            self.save_tasks(tasks)
        return target

    def decompose_prd(self, prd_content: str, feature_prefix: str = "TASK") -> List[MicroTask]:
        """Decomposes markdown PRD or Ask brief into structured dependency-aware microtasks."""
        lines = prd_content.splitlines()
        tasks: List[MicroTask] = []

        # 1. Look for explicit Acceptance Criteria or MoSCoW Must-haves
        items = []
        in_ac_section = False
        in_must_section = False

        for line in lines:
            line_s = line.strip()
            if re.search(r"##.*(?:Acceptance Criteria|Requirements|Features)", line_s, re.I):
                in_ac_section = True
                in_must_section = False
                continue
            elif re.search(r"- Must Have \(M\):", line_s, re.I):
                in_must_section = True
                in_ac_section = False
                must_items = line_s.replace("- Must Have (M):", "").strip()
                for mi in must_items.split(","):
                    if mi.strip():
                        items.append(mi.strip())
                continue
            elif line_s.startswith("## "):
                in_ac_section = False
                in_must_section = False

            if in_ac_section and line_s.startswith("- [ ]") or line_s.startswith("- "):
                clean = re.sub(r"^-\s*(\[[ xX]\])?\s*", "", line_s).strip()
                if clean and clean not in items:
                    items.append(clean)

        if not items:
            # Fallback: scan for any bullet items under Stage 2 or Stage 4
            for line in lines:
                m = re.match(r"^-\s*([A-Z0-9_\-]+:\s*.+)$", line.strip())
                if m:
                    items.append(m.group(1))

        if not items:
            items = ["Initialize domain interfaces and contracts", "Implement core domain logic", "Verify edge case invariants"]

        # Build dependency-chained microtasks
        for idx, item in enumerate(items, 1):
            tid = f"{feature_prefix}-{idx:02d}"
            deps = [f"{feature_prefix}-{idx-1:02d}"] if idx > 1 else []
            complexity = 3 if idx == 1 else (5 if "core" in item.lower() or "logic" in item.lower() else 4)

            tasks.append(
                MicroTask(
                    id=tid,
                    title=item.split(":", 1)[-1].strip() if ":" in item else item,
                    description=f"Implement and satisfy: {item}",
                    dependencies=deps,
                    complexity=complexity,
                    status="TODO",
                    acceptance_criteria=[item]
                )
            )

        self.save_tasks(tasks)
        return tasks

    def expand_task(self, task_id: str, subtask_titles: List[str]) -> List[MicroTask]:
        """Expands a complex task (complexity > 5) into smaller subtasks."""
        tasks = self.load_tasks()
        parent = None
        for t in tasks:
            if t.id.lower() == task_id.lower():
                parent = t
                break
        if not parent:
            raise ValueError(f"Task {task_id} not found.")

        created_subtasks: List[MicroTask] = []
        for idx, title in enumerate(subtask_titles, 1):
            sub_id = f"{parent.id}.{idx}"
            deps = [f"{parent.id}.{idx-1}"] if idx > 1 else list(parent.dependencies)
            sub = MicroTask(
                id=sub_id,
                title=title,
                description=f"Subtask for {parent.id}: {title}",
                dependencies=deps,
                complexity=max(1, parent.complexity - 2),
                status="TODO",
                parent_id=parent.id
            )
            created_subtasks.append(sub)
            if sub_id not in parent.subtasks:
                parent.subtasks.append(sub_id)

        all_tasks = tasks + created_subtasks
        self.save_tasks(all_tasks)
        return created_subtasks

    def add_task(
        self,
        task_id: str,
        title: str,
        description: str = "",
        dependencies: Optional[List[str]] = None,
        complexity: int = 3,
        target_files: Optional[List[str]] = None
    ) -> MicroTask:
        """Creates a new task in registry."""
        tasks = self.load_tasks()
        if any(t.id.lower() == task_id.lower() for t in tasks):
            raise ValueError(f"Task {task_id} already exists.")
        new_task = MicroTask(
            id=task_id,
            title=title,
            description=description,
            dependencies=dependencies or [],
            complexity=complexity,
            target_files=target_files or []
        )
        tasks.append(new_task)
        self.save_tasks(tasks)
        return new_task

    def remove_task(self, task_id: str) -> bool:
        """Removes a task and updates dependencies."""
        tasks = self.load_tasks()
        filtered = [t for t in tasks if t.id.lower() != task_id.lower() and t.parent_id != task_id]
        if len(filtered) == len(tasks):
            return False
        # Clean up dangling dependencies
        for t in filtered:
            if task_id in t.dependencies:
                t.dependencies.remove(task_id)
        self.save_tasks(filtered)
        return True

    def add_dependency(self, task_id: str, depends_on_id: str) -> bool:
        """Adds a dependency relationship."""
        tasks = self.load_tasks()
        target = next((t for t in tasks if t.id.lower() == task_id.lower()), None)
        if not target:
            return False
        if depends_on_id not in target.dependencies and depends_on_id != target.id:
            target.dependencies.append(depends_on_id)
            self.save_tasks(tasks)
            return True
        return False

    def remove_dependency(self, task_id: str, depends_on_id: str) -> bool:
        """Removes a dependency relationship."""
        tasks = self.load_tasks()
        target = next((t for t in tasks if t.id.lower() == task_id.lower()), None)
        if not target or depends_on_id not in target.dependencies:
            return False
        target.dependencies.remove(depends_on_id)
        self.save_tasks(tasks)
        return True

    def add_subtask(self, parent_id: str, title: str, complexity: int = 2) -> Optional[MicroTask]:
        """Adds a single subtask to a parent task."""
        tasks = self.load_tasks()
        parent = next((t for t in tasks if t.id.lower() == parent_id.lower()), None)
        if not parent:
            return None
        sub_idx = len(parent.subtasks) + 1
        sub_id = f"{parent.id}.{sub_idx}"
        sub = MicroTask(
            id=sub_id,
            title=title,
            description=f"Subtask for {parent.id}: {title}",
            dependencies=[parent.subtasks[-1]] if parent.subtasks else list(parent.dependencies),
            complexity=complexity,
            status="TODO",
            parent_id=parent.id
        )
        parent.subtasks.append(sub_id)
        tasks.append(sub)
        self.save_tasks(tasks)
        return sub

    def remove_subtask(self, parent_id: str, subtask_id: str) -> bool:
        """Removes a subtask from a parent task and registry."""
        tasks = self.load_tasks()
        parent = next((t for t in tasks if t.id.lower() == parent_id.lower()), None)
        if parent and subtask_id in parent.subtasks:
            parent.subtasks.remove(subtask_id)
        filtered = [t for t in tasks if t.id.lower() != subtask_id.lower()]
        if len(filtered) == len(tasks):
            return False
        # Clean up dangling dependencies
        for t in filtered:
            if subtask_id in t.dependencies:
                t.dependencies.remove(subtask_id)
        self.save_tasks(filtered)
        return True

    def fix_dependencies(self) -> Dict[str, Any]:
        """Removes dangling dependencies that point to non-existent tasks."""
        tasks = self.load_tasks()
        task_map = {t.id: t for t in tasks}
        fixed_count = 0
        removed = {}
        for t in tasks:
            valid_deps = []
            for dep in t.dependencies:
                if dep in task_map:
                    valid_deps.append(dep)
                else:
                    removed.setdefault(t.id, []).append(dep)
                    fixed_count += 1
            t.dependencies = valid_deps
        if fixed_count > 0:
            self.save_tasks(tasks)
        return {
            "fixed_count": fixed_count,
            "removed_dangling_dependencies": removed,
            "status": "HEALTHY" if fixed_count == 0 else "FIXED"
        }

    def validate_dependencies(self) -> Dict[str, Any]:
        """Detects circular dependencies, missing parent IDs, and bottlenecks."""
        tasks = self.load_tasks()
        task_map = {t.id: t for t in tasks}
        missing_deps = {}
        cycles = []

        for t in tasks:
            for dep in t.dependencies:
                if dep not in task_map:
                    missing_deps.setdefault(t.id, []).append(dep)

        # Cycle detection via DFS
        visited = set()
        rec_stack = set()

        def dfs(node_id: str, path: List[str]):
            visited.add(node_id)
            rec_stack.add(node_id)
            node = task_map.get(node_id)
            if node:
                for dep in node.dependencies:
                    if dep not in visited:
                        dfs(dep, path + [dep])
                    elif dep in rec_stack:
                        cycles.append(" -> ".join(path + [dep]))
            rec_stack.remove(node_id)

        for t in tasks:
            if t.id not in visited:
                dfs(t.id, [t.id])

        return {
            "valid": len(missing_deps) == 0 and len(cycles) == 0,
            "total_tasks": len(tasks),
            "missing_dependencies": missing_deps,
            "circular_dependencies": cycles
        }

    def analyze_complexity(self) -> Dict[str, Any]:
        """Produces a project complexity report and surfaces candidates for expansion."""
        tasks = self.load_tasks()
        if not tasks:
            return {"total_tasks": 0, "avg_complexity": 0.0, "high_complexity_tasks": []}

        total_cmplx = sum(t.complexity for t in tasks)
        avg = total_cmplx / len(tasks)
        high = [t.to_dict() for t in tasks if t.complexity >= 6]

        return {
            "total_tasks": len(tasks),
            "average_complexity": round(avg, 2),
            "high_complexity_count": len(high),
            "candidates_for_expansion": high
        }
