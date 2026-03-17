Use D3.js (v6) to build a public library circulation explorer from `/root/data/library_circulation.csv`.

Return the result as a single-page web app at `/root/output/circulation-treemap.html`. I should be able to open it in a browser without relying on CDN assets.

Also generate these local support files:
- `/root/output/js/d3.v6.min.js`
- `/root/output/data/library_circulation.csv`

The page should focus on a zoomable treemap:

1. Build a hierarchy with `All Branches` at the top level, `branch` as the next level, and `genre` as the leaf level.
   - Size treemap tiles by `annual_checkouts`.
   - The initial view should show branch totals.
   - Clicking a branch should zoom into that branch so the genre tiles fill the chart.
   - Provide a breadcrumb trail above the chart that always shows the current path and lets me return to the root view.

2. Keep the treemap readable and self-explanatory.
   - Every visible tile should have a stable text label showing the node name and its annual circulation total.
   - Use a consistent color system so each branch is easy to distinguish and its zoomed-in genre view still feels related to that branch.
   - The layout should remain readable on smaller screens as well as wider screens.

3. Add hover summaries.
   - On branch tiles, the tooltip should summarize the branch name, neighborhood, total annual checkouts, total unique titles, total renewals, average wait time, and dominant genre.
   - On genre tiles, the tooltip should summarize the branch, genre, audience, annual checkouts, unique titles, renewals, and average wait time.

Make the result polished and self-contained in the generated files.
