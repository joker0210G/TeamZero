"""TeamZero Generational Task Loop Engine (Generational Research Loops).

When tasks go through repair cycles or founder escalations, task state advances across Generations:
- Generation 1: Initial exploration
- Generation 2+: Inherits hard constraints from prior generation's failures
- Prevents re-learning and tracks cross-generation token burn.
"""

from __future__ import annotations
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from teamzero.config import TASKS_DIR
from teamzero.evidence import EvidenceGraph


@dataclass
class TaskState:
    task_id: str
    generation: int = 1
    status: str = "IN_PROGRESS"  # IN_PROGRESS | ESCALATED | COMPLETED
    cumulative_cost_tokens: int = 0
    inherited_constraints: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    inherited_evidence_nodes: List[str] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TaskState:
        return cls(
            task_id=data["task_id"],
            generation=data.get("generation", 1),
            status=data.get("status", "IN_PROGRESS"),
            cumulative_cost_tokens=data.get("cumulative_cost_tokens", 0),
            inherited_constraints=data.get("inherited_constraints", []),
            open_questions=data.get("open_questions", []),
            inherited_evidence_nodes=data.get("inherited_evidence_nodes", []),
            history=data.get("history", []),
            created_at=data.get("created_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        )


class TaskManager:
    """Manages generational tasks in .teamzero/memory/tasks/."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or TASKS_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def get_or_create_task(self, task_id: str) -> TaskState:
        path = self.storage_dir / f"{task_id}.yaml"
        if path.exists():
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                return TaskState.from_dict(data)
            except Exception:
                pass
        task = TaskState(task_id=task_id)
        self.save_task(task)
        return task

    def save_task(self, task: TaskState):
        path = self.storage_dir / f"{task.task_id}.yaml"
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(task.to_dict(), f, sort_keys=False)

    def advance_generation(
        self,
        task_id: str,
        reason: str,
        additional_constraints: Optional[List[str]] = None,
        tokens_spent: int = 0
    ) -> TaskState:
        """Rolls a task into Generation N+1 with inherited constraints from prior evidence."""
        task = self.get_or_create_task(task_id)
        ev_graph = EvidenceGraph()

        # Gather open evidence nodes from this task
        open_nodes = ev_graph.list_nodes(task_id=task_id, status="OPEN")
        new_inherited_nodes = [n.node_id for n in open_nodes]
        new_constraints = list(task.inherited_constraints)

        # Convert evidence findings into hard constraints
        for node in open_nodes:
            constraint = f"Guard against: {node.claim}"
            if constraint not in new_constraints:
                new_constraints.append(constraint)

        if additional_constraints:
            for ac in additional_constraints:
                if ac not in new_constraints:
                    new_constraints.append(ac)

        # Record generation history
        task.history.append({
            "generation": task.generation,
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "reason": reason,
            "tokens_spent": tokens_spent
        })

        task.generation += 1
        task.cumulative_cost_tokens += tokens_spent
        task.status = "IN_PROGRESS"
        task.inherited_constraints = new_constraints
        task.inherited_evidence_nodes = list(set(task.inherited_evidence_nodes + new_inherited_nodes))

        self.save_task(task)
        return task
