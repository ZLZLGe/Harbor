from __future__ import annotations

import heapq
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TaskNode:
    id: str
    dependencies: tuple[str, ...]
    priority: int


@dataclass(frozen=True)
class TaskGraph:
    graph_id: str
    tasks: tuple[TaskNode, ...]


class GraphValidationError(Exception):
    def __init__(self, issues: list[dict[str, str]]) -> None:
        super().__init__("invalid graph")
        self.issues = issues


class DependencyPlanner:
    def __init__(self, graph: TaskGraph) -> None:
        self.graph = graph
        self.task_by_id = {task.id: task for task in graph.tasks}

    def validate(self) -> None:
        counts = Counter(task.id for task in self.graph.tasks)
        issues: list[dict[str, str]] = []

        for task_id, count in sorted(counts.items()):
            if count > 1:
                issues.append({"kind": "duplicate-task", "taskId": task_id})

        known_ids = set(self.task_by_id)
        for task in sorted(self.graph.tasks, key=lambda item: item.id):
            for dependency_id in sorted(task.dependencies):
                if dependency_id not in known_ids:
                    issues.append(
                        {
                            "kind": "unknown-dependency",
                            "taskId": task.id,
                            "dependencyId": dependency_id,
                        }
                    )

        if issues:
            raise GraphValidationError(issues)

    def stable_topological_order(self) -> tuple[list[str], list[str]]:
        indegree = {task.id: len(task.dependencies) for task in self.graph.tasks}
        dependents: dict[str, list[str]] = defaultdict(list)

        for task in self.graph.tasks:
            for dependency_id in task.dependencies:
                dependents[dependency_id].append(task.id)

        ready: list[tuple[int, str]] = []
        for task in self.graph.tasks:
            if indegree[task.id] == 0:
                heapq.heappush(ready, (task.priority, task.id))

        ordered: list[str] = []
        while ready:
            _, task_id = heapq.heappop(ready)
            if task_id not in indegree:
                continue

            ordered.append(task_id)
            indegree.pop(task_id)

            for dependent_id in dependents.get(task_id, []):
                if dependent_id not in indegree:
                    continue
                indegree[dependent_id] -= 1
                if indegree[dependent_id] == 0:
                    heapq.heappush(
                        ready,
                        (self.task_by_id[dependent_id].priority, dependent_id),
                    )

        remaining = sorted(task_id for task_id, degree in indegree.items() if degree > 0)
        return ordered, remaining

    def find_cycles(self, remaining: list[str]) -> list[list[str]]:
        remaining_set = set(remaining)
        adjacency = {
            task.id: [dep for dep in task.dependencies if dep in remaining_set]
            for task in self.graph.tasks
            if task.id in remaining_set
        }

        index = 0
        stack: list[str] = []
        on_stack: set[str] = set()
        indices: dict[str, int] = {}
        lowlinks: dict[str, int] = {}
        components: list[list[str]] = []

        def strong_connect(node_id: str) -> None:
            nonlocal index
            indices[node_id] = index
            lowlinks[node_id] = index
            index += 1
            stack.append(node_id)
            on_stack.add(node_id)

            for next_id in adjacency.get(node_id, []):
                if next_id not in indices:
                    strong_connect(next_id)
                    lowlinks[node_id] = min(lowlinks[node_id], lowlinks[next_id])
                elif next_id in on_stack:
                    lowlinks[node_id] = min(lowlinks[node_id], indices[next_id])

            if lowlinks[node_id] == indices[node_id]:
                component: list[str] = []
                while stack:
                    member = stack.pop()
                    on_stack.remove(member)
                    component.append(member)
                    if member == node_id:
                        break

                component.sort()
                if len(component) > 1 or node_id in adjacency.get(node_id, []):
                    components.append(component)

        for node_id in sorted(remaining):
            if node_id not in indices:
                strong_connect(node_id)

        components.sort(key=lambda items: items[0])
        return components

    def plan(self) -> dict[str, object]:
        self.validate()
        execution_order, remaining = self.stable_topological_order()
        cycles = self.find_cycles(remaining) if remaining else []
        status = "cycle" if cycles else "planned"
        unresolved = sorted({task_id for cycle in cycles for task_id in cycle})

        return {
            "graphId": self.graph.graph_id,
            "status": status,
            "executionOrder": execution_order,
            "cycles": cycles,
            "unresolved": unresolved,
            "errors": [],
        }


def load_graphs(path: Path) -> list[TaskGraph]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    graphs: list[TaskGraph] = []
    for raw_graph in payload["graphs"]:
        tasks = tuple(
            TaskNode(
                id=raw_task["id"],
                dependencies=tuple(raw_task["dependencies"]),
                priority=int(raw_task["priority"]),
            )
            for raw_task in raw_graph["tasks"]
        )
        graphs.append(TaskGraph(graph_id=raw_graph["graphId"], tasks=tasks))
    return graphs


def render_reports(graphs: list[TaskGraph]) -> dict[str, object]:
    reports: list[dict[str, object]] = []
    for graph in graphs:
        planner = DependencyPlanner(graph)
        try:
            reports.append(planner.plan())
        except GraphValidationError as exc:
            unresolved = sorted({issue["taskId"] for issue in exc.issues})
            reports.append(
                {
                    "graphId": graph.graph_id,
                    "status": "invalid",
                    "executionOrder": [],
                    "cycles": [],
                    "unresolved": unresolved,
                    "errors": exc.issues,
                }
            )
    return {"reports": reports}


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        raise SystemExit("usage: DependencyPlanner.py <input-json> <output-json>")

    input_path = Path(argv[1])
    output_path = Path(argv[2])
    output_path.write_text(
        json.dumps(render_reports(load_graphs(input_path)), indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
