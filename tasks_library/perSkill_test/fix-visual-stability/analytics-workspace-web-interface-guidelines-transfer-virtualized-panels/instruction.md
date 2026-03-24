There is a Next.js analytics workspace at `/app`. The activity view feels unstable because the main table does too much work during scroll, the summary panels keep reflowing during navigation, and the current rendering approach is too expensive for a large feed.

Your job is to make the workspace feel stable and responsive without changing the existing monitoring workflow.

## Rules

- Do not break the current section switching or filtering behavior
- Do not change existing class names, ids, or `data-testid` values because the tests rely on them
- Keep `src/components/AnalyticsTable.tsx` as the main file under review
