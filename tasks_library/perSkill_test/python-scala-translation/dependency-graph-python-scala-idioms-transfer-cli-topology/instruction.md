# Transfer - Dependency Graph CLI Translation

`/root/DependencyPlanner.py` contains a Python command-line planner that reads JSON task graphs, computes a stable execution order, and reports cycle or validation problems. Translate it into idiomatic Scala 2.13 and save the result as `/root/DependencyPlannerApp.scala`.

Your Scala file must compile under Scala 2.13, use package `dependencyplanner`, and expose this translated public surface:

- `final case class TaskNode`
- `final case class TaskGraph`
- `sealed trait PlannerIssue`
- `final case class DuplicateTask`
- `final case class UnknownDependency`
- `final case class TopologySnapshot`
- `final case class PlanReport`
- `object DependencyPlanner` with `fromJson`, `stableTopologicalOrder`, `findCycles`, `plan`, `planAll`, and `renderReports`
- `object DependencyPlannerApp` with `main(args: Array[String]): Unit`

Behavioral requirements:

- The CLI must read an input JSON file and write an output JSON file.
- The input shape is:
  - a root object with `graphs`
  - each graph has `graphId` and `tasks`
  - each task has `id`, `dependencies`, and `priority`
- The CLI is invoked as `runMain dependencyplanner.DependencyPlannerApp <input-json> <output-json>`.
- The output shape must be:
  - a root object with `reports`
  - each report has `graphId`, `status`, `executionOrder`, `cycles`, `unresolved`, and `errors`
- `status` must be one of:
  - `"planned"` for valid acyclic graphs
  - `"cycle"` for valid graphs that still have unresolved cycle members after planning
  - `"invalid"` for graphs with duplicate task ids or missing dependencies
- Planning must be stable:
  - when multiple tasks are ready at the same time, pick lower `priority` first
  - break remaining ties by lexicographically smaller task id
- For `"cycle"` reports:
  - `executionOrder` must contain the maximal stable prefix that can be scheduled before the graph gets stuck
  - `cycles` must contain unresolved strongly connected components, with each cycle sorted lexicographically
  - the list of cycles must be ordered by the first task id in each cycle
  - `unresolved` must be the sorted distinct union of all ids that appear in `cycles`
- For `"invalid"` reports:
  - `executionOrder` must be empty
  - `cycles` must be empty
  - `unresolved` must be the sorted distinct set of task ids mentioned by the validation errors
- Error objects in `errors` must use one of these shapes:
  - `{"kind":"duplicate-task","taskId":"..."}`
  - `{"kind":"unknown-dependency","taskId":"...","dependencyId":"..."}`
- `DependencyPlanner.plan` must return `Either[Vector[PlannerIssue], PlanReport]` so invalid graphs are modeled as typed errors instead of exceptions.
- `DependencyPlanner.fromJson` must return `Either[String, Vector[TaskGraph]]` for malformed input payloads.

Data-modeling requirements:

- Use immutable case classes for the graph and report data.
- Model planner issues with a sealed hierarchy.
- Use `Either` and `Option` where absence or failure is part of the contract.
- Use pattern matching for issue rendering or result handling.
- Do not use `null` to represent missing data.

The bundled tests will compile your Scala file, run generated probes against the public API, execute the CLI on `/root/task_graphs.json`, and validate the observable JSON results. `/root/task_graphs.json` is included only as a quick sanity-check asset.
