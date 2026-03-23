You are preparing ground-traffic action sequences for airport operations using PDDL planning inputs.

Inputs:
- `/app/problem.json`: list of planning cases. Each case contains `id`, `domain`, `problem`, and `plan_output`.
- Domain and problem files referenced by each case under `/app/airport/`.

Task requirements:
1. Read every case in `/app/problem.json`.
2. For each case, load the referenced domain and problem files.
3. Produce a valid sequential plan that solves the case goal.
4. Write the plan to the exact `plan_output` path from that case.

Plan format requirements:
- One action per line.
- Each line must use standard action syntax with parentheses.
- Action and object names must match the referenced PDDL files.
- Every generated plan must be executable and goal-valid under the given domain/problem pair.

Scenario context:
This Transfer task reframes the planning primitive as a turnaround wave scheduling pack for a different operations window.
