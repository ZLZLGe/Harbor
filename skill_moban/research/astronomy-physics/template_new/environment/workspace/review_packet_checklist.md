# Follow-Up Packet Checklist

- Reconstruct each candidate from detector-space pixels into sky coordinates using the bundled FITS WCS.
- Use the bundled visit manifest for observation times, exposure lengths, zeropoints, and extinction values.
- Match every candidate against the bundled Gaia foreground slice and the host-galaxy table.
- Use the bundled review rules for screening decisions and the reported distance-model metadata.
- Produce all five deliverables under `/root/answer`.
- Keep the packet tables and `briefing.json` mutually consistent.
