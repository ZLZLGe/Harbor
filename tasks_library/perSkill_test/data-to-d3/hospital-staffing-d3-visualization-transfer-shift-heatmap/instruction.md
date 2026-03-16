Use D3.js (v6) to build a hospital staffing dashboard from these local files:
- `/root/data/staffing_heatmap.csv`
- `/root/data/unit_hourly_gaps.csv`

Return the result as a single-page web app at `/root/output/staffing-heatmap.html`. I should be able to open it in a browser without relying on CDN assets.

Also generate these local support files:
- `/root/output/js/d3.v6.min.js`
- `/root/output/data/staffing_heatmap.csv`
- `/root/output/data/unit_hourly_gaps.csv`

The dashboard should have two synchronized panels:

1. A weekday-by-shift heatmap for staffing pressure.
   - Use weekdays on one axis and the three shifts (`Night`, `Day`, `Evening`) on the other.
   - Each heatmap cell should encode `average_gap` with color intensity.
   - Label every cell with the average staffing gap value.
   - Include axis labels and a clear color legend.
   - On hover, show a tooltip with the weekday, shift, average gap, peak hour, peak gap, required staff total, scheduled staff total, and the units listed in `units_above_gap_4`.

2. A synchronized unit-level hourly trend panel.
   - When a heatmap cell is clicked, show a line chart of hourly `staffing_gap` values for each unit during that exact weekday-shift selection.
   - When a weekday label or row is clicked, switch the panel to a day overview that shows all hours for that weekday across shifts.
   - Use a separate colored line for each unit and include a legend.
   - Show point markers for each hourly observation.
   - Update the panel title or subtitle so the current selection is always obvious.

Interaction and layout requirements:
- The selected heatmap cell should be visually highlighted.
- A selected weekday row should be visually highlighted when the day overview mode is active.
- The two panels should appear side by side on wider screens and remain readable on smaller screens.
- Keep the presentation polished and self-contained in the generated output.
