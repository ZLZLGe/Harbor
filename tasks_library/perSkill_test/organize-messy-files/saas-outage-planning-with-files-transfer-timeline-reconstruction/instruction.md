You are working in `/root`.

An incident workspace is available at `/root/incident_workspace`. It contains logs, alert exports, on-call chat notes, incident tickets, and configuration snapshots from a checkout outage at a SaaS company.

Your job:

1. Review the evidence in `/root/incident_workspace`.
2. Reconstruct the outage timeline in UTC.
3. Write `/root/reports/outage_postmortem.md`.
4. Keep three working notes in `/root` while you investigate:
   - `task_plan.md`
   - `findings.md`
   - `progress.md`

Requirements for `/root/reports/outage_postmortem.md`:

- Include these exact section headings:
  - `# Outage Postmortem`
  - `## Executive Summary`
  - `## Customer Impact`
  - `## Timeline`
  - `## Root Cause Hypothesis`
  - `## Key Evidence`
  - `## Open Questions`
- The timeline section must be a Markdown table with at least 6 incident events in chronological order.
- Each timeline row must include:
  - a UTC timestamp,
  - a short event description,
  - the evidence file or files that support the row.
- The customer impact section must identify the affected product surface and the outage window.
- The root cause hypothesis section must explain the most likely trigger, the technical mechanism, and why it is more plausible than other leads in the workspace.
- The key evidence section must contain at least 4 bullet points and each bullet must reference specific files from `/root/incident_workspace`.
- The open questions section must contain at least 2 bullet points.

Do not modify the incident evidence files. The goal is to analyze them and produce the report and working notes.
