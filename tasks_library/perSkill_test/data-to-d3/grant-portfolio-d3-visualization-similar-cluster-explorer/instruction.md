Use D3.js (v6) to build a university grant portfolio explorer from the data at `/root/data/grants.csv`.

Return the result as a single-page web app at `/root/output/grant-clusters.html`. I should be able to open it in a browser without relying on CDN assets.

Also generate these local support files:
- `/root/output/js/d3.v6.min.js`
- `/root/output/data/grants.csv`

The page should present two coordinated views:

1. A force-clustered bubble chart for all grants.
   - Each bubble represents one grant.
   - Bubble size should reflect `award_amount`.
   - Bubble color should reflect `sponsor_type`.
   - Use a D3 force simulation so grants with the same sponsor type cluster together, stay reasonably centered in the chart, and do not overlap.
   - Include a legend that lists every sponsor type shown in the data.
   - Label each bubble with its `grant_id`.
   - On hover, show a tooltip with the grant ID, university, project title, sponsor, sponsor type, award amount, and start year.

2. A linked grants table.
   - Include every grant in the dataset.
   - Show these columns exactly: `Grant ID`, `University`, `Project`, `Sponsor Type`, `Award Amount`, and `Start Year`.
   - Default sort order should be award amount descending.
   - Clicking a column header should sort by that column, and repeated clicks on the same header should toggle ascending/descending.

The chart and table must be linked:
- Clicking a bubble highlights the matching table row.
- Clicking a table row highlights the matching bubble.
- The selected row and selected bubble should both be visually obvious.

Lay the bubble chart and table side by side on wider screens, while remaining readable on smaller screens.
