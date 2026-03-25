You are preparing a survey digest for a set of drone mission cases.

The case manifest is stored at `/root/survey_batch.json`. Each case gives you:
1. A PDDL domain file path.
2. A PDDL problem file path.
3. The exact output path where the plan must be written.

For every case in the manifest:
1. Load the listed PDDL domain and PDDL problem.
2. Generate a valid sequential plan that solves the case.
3. Write the plan to the exact `plan_output` path listed in the manifest.

After all plans are written, create `/root/transfer3_survey_digest.txt`.

Write the digest as repeated blocks in this exact key-value format:

```text
case_id=<case id>
plan_file=<plan path>
steps=<number of non-empty action lines>
capture_actions=<number of capture-photo actions>
final_action=<last non-empty action line>
```

Rules:
1. Sort the blocks by `case_id` ascending.
2. Separate blocks with a single blank line.
3. `plan_file` must exactly match the plan path for that case.
4. `steps` must equal the number of non-empty action lines in the plan file.
5. `capture_actions` must equal the number of actions whose name is `capture-photo`.
6. `final_action` must be the last non-empty action line in the plan file.
7. Every generated plan must be syntactically valid and solve its listed PDDL problem.
