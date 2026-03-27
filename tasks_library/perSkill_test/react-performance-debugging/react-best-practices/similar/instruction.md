There's a Next.js application for meridian gear shop that feels noticeably slow in production. Some recurring complaints:

- Add to Cart actions are slow
- `/compare` is slow to load the first time
- `/api/products` and `/api/checkout` respond slower than expected

Your job is to use React and Next.js patterns and best practices to assess the root cause of the performance issues and fix them.
Focus on API route optimization, bundle size reduction, and excessive rendering.

The app must work properly:

- Homepage must show product data
- Add to Cart must update the cart counter
- `/compare` advanced tab must render properly (don't remove `data-testid="advanced-content"`)

Constraints:

- Do not modify `data-testid` attributes or remove any component using them
- Do not remove `performance.mark()` calls from `CatalogCard`
