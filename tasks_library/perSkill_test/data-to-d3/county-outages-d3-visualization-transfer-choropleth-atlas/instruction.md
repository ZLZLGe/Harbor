Use D3.js (v6) to build a county outage atlas from these local files:
- `/root/data/county_outages.csv`
- `/root/data/county_boundaries.geojson`

Return the result as a single-page web app at `/root/output/outage-atlas.html`. I should be able to open it in a browser without relying on CDN assets.

Also generate these local support files:
- `/root/output/js/d3.v6.min.js`
- `/root/output/data/county_outages.csv`
- `/root/output/data/county_boundaries.geojson`

The page should include three coordinated pieces:

1. A county choropleth map.
   - Draw every county from the GeoJSON.
   - Color each county by `severity_index` from the CSV.
   - Add a clear legend with at least five severity bands from lower severity to higher severity.
   - On hover, show county details including county name, customers out, percent affected, restoration ETA, and the listed critical facility.
   - Clicking a county should lock the selection and make the selected county visually distinct.

2. A ranked county bar chart.
   - Include every county in the CSV.
   - Sort the bars by `severity_index` descending.
   - Use the same severity color encoding as the map.
   - Show county names and severity values clearly enough to read.
   - Hovering or clicking a bar should synchronize with the map and the details panel.

3. A details panel for the current county.
   - Show the currently active county and its metrics in a readable summary.
   - Start with the highest-severity county selected by default.
   - Keep the details panel synchronized with hover and click interactions from both the map and the ranked bars.

Layout requirements:
- Keep the map and ranked chart side by side on wider screens while remaining readable on smaller screens.
- Make the output polished and self-contained in the generated files.
