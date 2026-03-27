You are preparing a warehouse restocking dispatch packet.

The case manifest is stored at `/root/warehouse_batch.json`. Each case gives you:
1. A PDDL domain file path.
2. A PDDL problem file path.
3. The exact output path where the plan must be written.

For every case in the manifest:
1. Load the listed PDDL domain and PDDL problem.
2. Generate a valid sequential plan that solves the case.
3. Write the plan to the exact `plan_output` path listed in the manifest.

After all plans are written, create `/root/transfer1_warehouse_dispatch.csv`.

Write the CSV with this header:
`case_id,plan_file,steps,pick_actions,drop_actions`

Rules:
1. Sort rows by `case_id` ascending.
2. `plan_file` must exactly match the plan path for that case.
3. `steps` must equal the number of non-empty action lines in the plan file.
4. `pick_actions` must equal the number of actions whose name is `pick`.
5. `drop_actions` must equal the number of actions whose name is `drop`.
6. Every generated plan must be syntactically valid and solve its listed PDDL problem.
