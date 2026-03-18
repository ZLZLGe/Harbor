# Fragment Cleanliness Policy

Reverse-engineering scans are accepted only when the disconnected debris volume stays within the QA limit below.

| Metric | Limit | Interpretation |
| --- | --- | --- |
| Max debris-volume ratio | 5.0% | Reject the scan if debris volume exceeds this share of the total scanned volume. |

Reporting rule:
- Report the threshold in `/root/fragment_audit.json` as a decimal ratio.
