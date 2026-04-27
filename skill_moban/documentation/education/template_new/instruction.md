You are helping the curriculum operations team turn a real course-production incident into a reusable agent skill.

The input data is in `/workspace/session_bundle/`. It contains exported support tickets, reviewer comments, CI logs, course metadata snapshots, style-guide excerpts, repository convention snapshots, and a local knowledge service manifest. The local knowledge service is available at `http://127.0.0.1:8080` and exposes the same incident records in API form for cross-checking.

The task also provides a process skill at `/workspace/environment/skills/update-skills/SKILL.md`. Use it as process evidence for the capture decision, cite it in your evidence, and do not modify it.

Your task:

1. Review the session bundle and identify the durable learning behind the incident. Focus on the reusable workflow, non-obvious constraints, failure pattern, and evidence that would help a future agent avoid the same mistake.

2. Decide whether the learning should be captured as a standalone skill, an update to an existing skill, a learning added to an existing instruction, or a new repository instruction. Use the existing repository conventions in the input bundle to justify the decision and avoid duplicating knowledge already captured elsewhere.

3. Create a new skill draft at `/outputs/lesson_skill/SKILL.md`.

4. Create a structured capture report at `/outputs/capture_report.json`.

Output format:

`/outputs/lesson_skill/SKILL.md` must be a valid agent skill document with YAML frontmatter:

```markdown
---
name: <lowercase-hyphenated-name>
description: <one sentence describing when to use this skill>
---

# <Skill Title>

<skill body>
```

The skill body must include these sections:

```markdown
## When to Use
## Evidence Reviewed
## Procedure
## Quality Checks
## Example
```

`/outputs/capture_report.json` must use this shape:

```json
{
  "decision": "skill",
  "skill_name": "lowercase-hyphenated-name",
  "incident_summary": "one or two sentences",
  "root_cause": "one or two sentences",
  "evidence": [
    {
      "source": "relative path or API endpoint",
      "finding": "specific observation"
    }
  ],
  "reusable_principles": [
    "principle 1",
    "principle 2"
  ],
  "rejected_alternatives": [
    {
      "alternative": "short name",
      "reason": "why it was not sufficient"
    }
  ]
}
```

Requirements:

1. The skill must be general enough to help future course-production or educational-content agents, not just restate this single incident.
2. The skill must be specific enough to be actionable. Include concrete checks, decision points, and at least one example of a wrong approach and a corrected approach.
3. The evidence list must cite real files from `/workspace/session_bundle/`, the provided process skill at `/workspace/environment/skills/update-skills/SKILL.md`, or real local API endpoints from `http://127.0.0.1:8080`.
4. The rejected alternatives must explain why the learning is not just a brief learning added to an existing instruction and why it is not merely an update to an existing skill.
5. The output must not depend on hidden files, external accounts, or network services outside the provided environment.
6. Do not replace the real workflow with a fake summary, delete input data, bypass the local knowledge service, or modify the provided skills.
7. Do not edit files under `/workspace/session_bundle/`, `/workspace/environment/skills/`, or any existing repository skill directory. Put all deliverables under `/outputs/`.
