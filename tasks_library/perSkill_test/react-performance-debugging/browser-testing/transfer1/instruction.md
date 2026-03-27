Review the layout-shift evidence in `/root/data/` and write `/root/donation_layout_shift_audit.md`.

The page belongs to a donation flow that suffers from visible jumps after first paint. Use the supplied CLS capture, shift source notes, and page context to produce a short remediation memo.

Requirements:
- Keep the title exactly `# Donation Layout Shift Audit`.
- Report the current CLS score and rating from the capture.
- List the three highest-confidence causes in the order they should be addressed.
- Provide a three-step remediation order that maps directly to those causes.
- End with a one-line conclusion that states whether the page is ready to ship.

Output contract:
- Write Markdown only.
- Save the final file exactly as `/root/donation_layout_shift_audit.md`.
