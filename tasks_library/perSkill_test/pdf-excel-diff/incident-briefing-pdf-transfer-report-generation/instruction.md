You are preparing a leadership-ready incident briefing.

Input:
- `/root/incident_data.json`: structured briefing metadata, leadership actions, and incident records

Write the finished briefing document to the exact path `/root/incident_briefing_report.` followed immediately by the lowercase ASCII characters with decimal codes `112`, `100`, and `102`, in that order.

Requirements:

1. Generate a polished multi-page briefing titled `Incident Briefing Report`.
2. Set the document metadata title to `Incident Briefing Report`.
3. The opening section must include these lines using the values from the JSON file:
   - `Briefing Date: ...`
   - `Reporting Window: ...`
   - `Prepared For: ...`
   - `Prepared By: ...`
   - `Command Contact: ...`
4. Include an `Executive Summary` section that reports:
   - `Total Incidents`
   - `Open Incidents` where statuses `Active`, `Monitoring`, and `Mitigated` count as open
   - `Resolved Incidents`
   - `Highest Severity`
   - `Total Customers Impacted`
   - `Most Impacted Site`
5. Include a `Leadership Actions` section that lists every item from `leadership_actions`.
6. Include an `Incident Highlights` section with short narrative entries for the three incidents affecting the most customers.
7. Include a `Detailed Incident Log` table with one row per incident and these column headers:
   - `Incident ID`
   - `Title`
   - `Site`
   - `Severity`
   - `Status`
   - `Owner`
   - `Started`
   - `Duration (min)`
   - `Impacted Customers`
   - `Next Update`
8. Sort the incident log by severity rank (`SEV-1`, then `SEV-2`, then `SEV-3`), and within the same severity sort by `started_at` ascending.
9. Preserve every incident from the JSON input. Do not omit rows, merge incidents, or add fictional incidents.
10. The finished document must remain readable as a normal paginated report and span multiple pages.
