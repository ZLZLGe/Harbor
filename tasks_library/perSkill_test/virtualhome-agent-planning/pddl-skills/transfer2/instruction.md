You are preparing a lab assay runbook for a set of workflow cases.

The case manifest is stored at `/root/lab_batch.json`. Each case gives you:
1. A PDDL domain file path.
2. A PDDL problem file path.
3. The exact output path where the plan must be written.

For every case in the manifest:
1. Load the listed PDDL domain and PDDL problem.
2. Generate a valid sequential plan that solves the case.
3. Write the plan to the exact `plan_output` path listed in the manifest.

After all plans are written, create `/root/transfer2_lab_runbook.md`.

Write the runbook exactly in this structure:
1. A first line with `# Lab Runbook`
2. A blank line
3. A Markdown table with this header row:
   `| case_id | plan_file | steps | terminal_action |`
4. A separator row:
   `| --- | --- | ---: | --- |`

Rules:
1. Sort table rows by `case_id` ascending.
2. `plan_file` must exactly match the plan path for that case.
3. `steps` must equal the number of non-empty action lines in the plan file.
4. `terminal_action` must be the last non-empty action line in the plan file.
5. Every generated plan must be syntactically valid and solve its listed PDDL problem.
