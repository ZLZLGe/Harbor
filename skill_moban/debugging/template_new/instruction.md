You are the on-call engineer for a Next.js analytics dashboard with live browser regressions.

Inputs:
- `/app`: the application code under investigation
- hidden downstream service code under `/services/api-simulator` is part of the environment baseline and must not be edited

The dashboard currently exhibits three production symptoms:
- opening a linked alert on a cold browser start is visually unstable, and the same alert can come back under the wrong active filter after refresh
- the analytics timeline feels too heavy before advanced insights are explicitly opened
- repeated filtering, drawer toggling, and timeline refreshes gradually make the page less responsive until the tab is refreshed

Your job is to diagnose and fix the application in place.
Reproduce and measure the live browser behavior yourself. Focus on what the running app actually does.

Key business constraints:
- The dashboard homepage must continue rendering the real bundled analytics data
- The alert drawer flow must keep working with its public `data-testid` hooks intact
- The linked alert context must continue rendering as part of the alert detail experience on the dashboard deeplink path
- The advanced insights panel must keep rendering correctly; do not remove `data-testid="advanced-insights-panel"`
- The real downstream analytics service must remain part of the runtime path after your fix

Constraints:
- Do not modify `data-testid` attributes or remove any component using them
- Do not replace the real analytics snapshot with toy or synthetic data
- Do not edit hidden environment baseline files under `/services/api-simulator`
- Do not change the tests

Deliver the fix by modifying the application in `/app`.
