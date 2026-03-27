Review the before/after captures in `/root/data/` and write `/root/search_release_gate.txt`.

The snapshots come from a search experience that just received a performance patch. Use the measurement deltas and release guardrails to decide whether the patch can ship now or needs follow-up work.

Requirements:
- Keep the output as exactly six newline-terminated lines.
- Report the status, page delta, API delta, bundle delta, remaining risk, and next measurement.
- Use the provided guardrails when deciding whether the patch is ready.
- Preserve the numeric before/after values and percentages exactly in the final note.

Output contract:
- Write plain text only.
- Save the final file exactly as `/root/search_release_gate.txt`.
