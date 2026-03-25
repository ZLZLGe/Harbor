Create a single-page D3.js operations dashboard from the local CSV files `/root/data/route_performance.csv` and `/root/data/stop_delays.csv`.
This transfer task should be completed with the visualization tooling that is already available in the environment.

Write the final page to `/root/output/bus-reliability.html`. I should be able to open that HTML file in a browser without any network access.

Also generate these support files:
- `/root/output/assets/d3.v7.min.js`
- `/root/output/assets/app.js`
- `/root/output/assets/styles.css`
- `/root/output/assets/route_performance.csv` (copy of the provided CSV)
- `/root/output/assets/stop_delays.csv` (copy of the provided CSV)

The page should look like a transit operations dashboard and must include these inspectable sections:
- A route selector with `id="route-selector"`
- An SVG small-multiples chart with `id="reliability-small-multiples"`
- A focus readout with `id="focus-readout"`
- A summary card container with `id="interval-summary"`
- A stop detail table with `id="stop-detail-table"`

Use the input files to satisfy the following requirements:

1. Data preparation:
   - Treat each row in `route_performance.csv` as one route/time-bin observation.
   - Compute `on-time rate = on_time_trips / scheduled_trips`.
   - Compute each route's all-day rate from summed `scheduled_trips` and `on_time_trips` across all of its time bins.
   - Sort routes by all-day rate ascending, then by `route_id` ascending. Use that order consistently for the route selector and the small-multiple panels.
   - Use the `time_bin` values in ascending order along the x-axis.

2. Route selector:
   - Render one `<button class="route-chip">` per route.
   - Every route chip must include `data-route-id="<route id>"`.
   - The default selected route must be the route with the lowest all-day on-time rate.
   - Only the selected route chip may have `aria-pressed="true"`. All others must have `aria-pressed="false"`.

3. Small-multiple line charts:
   - Render one `<g class="route-panel" data-route-id="...">` per route.
   - Each route panel must include:
     - one `<path class="reliability-line" data-route-id="...">`
     - one `<circle class="time-point">` per time bin
     - one `<rect class="focus-band">` per time bin to capture hover interaction
   - Every time point must include these attributes:
     - `data-route-id`
     - `data-time-bin`
     - `data-on-time-rate` as a decimal rounded to 4 places
     - `data-late-trips` as an integer
   - Every focus band must include:
     - `data-route-id`
     - `data-time-bin`
     - `aria-current="true|false"`
   - Mark route panels with `data-selected="true|false"` so the active route is inspectable.
   - Use a fixed y-domain from 0% to 100% for every panel so the routes are directly comparable.

4. Focus behavior:
   - On first load, there is no active time-bin focus. The readout must reflect the selected route and `All day`.
   - Hovering a focus band inside the selected route panel must:
     - update `#focus-readout` to the selected route and hovered `time_bin`,
     - update `#interval-summary` to show that hovered interval's on-time rate, late trips, and scheduled trips,
     - set only the matching focus band to `aria-current="true"`,
     - update the stop detail table for the selected route and hovered time bin.
   - Leaving the selected route panel must clear the active time-bin focus, restore the all-day summary and all-day table for the selected route, and reset all focus bands to `aria-current="false"`.

5. Stop detail table:
   - The table must show the top 5 worst-performing stops for the current route scope.
   - Use these columns in this exact order:
     - `Stop`
     - `Late arrivals`
     - `10+ min delays`
     - `Arrivals`
     - `Late rate`
   - For the all-day scope, aggregate rows from `stop_delays.csv` across all time bins for the selected route.
   - For a focused interval, use only rows from the selected route and focused `time_bin`.
   - Sort table rows by:
     - `delays_over_10_min` descending,
     - then `late_arrivals` descending,
     - then `stop_id` ascending.
   - Every table row must include:
     - `data-route-id`
     - `data-stop-id`
     - `data-scope="all-day|<time_bin>"`

6. Route changes:
   - Clicking a route chip must switch the selected route, clear any active time-bin focus, update the readout, update the summary cards, and rebuild the detail table for that route's all-day scope.
   - After a route change, only the matching route panel may keep `data-selected="true"`.

7. Presentation:
   - Include a visible page title and short subtitle.
   - `#interval-summary` must present the current scope's on-time rate, late trips, and scheduled trips. You may include additional summary metrics if they are relevant.
   - Keep all assets local; do not rely on any CDN, remote API, or remote font.
   - The layout should remain readable on desktop and narrow screens.
