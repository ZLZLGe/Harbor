You are the on-call engineer for a Next.js reading-room storefront with a live runtime regression.

Inputs:
- `/app`: the application code under investigation
- hidden downstream service code under `/services/api-simulator` is part of the environment baseline and must not be edited

The storefront currently exhibits three user-visible regressions in production:
- a linked review entry is not visually stable on cold load and can come back in the wrong state after refresh
- the compare workspace feels too heavy before advanced analysis is explicitly opened
- repeated curation interactions make the page progressively less responsive until the tab is refreshed

Your job is to diagnose the root causes and fix the application in place.
Reproduce and measure the live browser behavior yourself. Focus on real runtime behavior rather than static guesswork.

Key business constraints:
- Homepage must continue rendering the real bundled catalog data
- The shortlist flow must keep working with its public `data-testid` hooks intact
- The compare advanced tab must keep rendering correctly; do not remove `data-testid="advanced-content"`
- The real downstream catalog service must remain part of the runtime path after your fix

Constraints:
- Do not modify `data-testid` attributes or remove any component using them
- Do not replace the real catalog snapshot with toy or synthetic data
- Do not edit hidden environment baseline files under `/services/api-simulator`
- Do not change the tests

Deliver the fix by modifying the application in `/app`.
