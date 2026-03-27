There's a Next.js application for northwind triage board that feels noticeably slow in production. Some recurring complaints:

- Watch Patient actions are slow
- `/triage` is slow to load the first time
- `/api/patients` and `/api/assignments` respond slower than expected

Your job is to use React and Next.js patterns and best practices to assess the root cause of the performance issues and fix them.
Focus on API route optimization, bundle size reduction, and excessive rendering.

The app must work properly:

- Homepage must show patient data
- Watch Patient must update the watchlist counter
- `/triage` advanced tab must render properly (don't remove `data-testid="advanced-content"`)

Constraints:

- Do not modify `data-testid` attributes or remove any component using them
- Do not remove `performance.mark()` calls from `CatalogCard`
