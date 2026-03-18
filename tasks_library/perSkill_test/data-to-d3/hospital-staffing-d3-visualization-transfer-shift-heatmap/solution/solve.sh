#!/bin/bash
set -euo pipefail

mkdir -p /root/output/js /root/output/data
cp /root/data/staffing_heatmap.csv /root/output/data/staffing_heatmap.csv
cp /root/data/unit_hourly_gaps.csv /root/output/data/unit_hourly_gaps.csv

mkdir -p /tmp/staffing-d3-lib
cd /tmp/staffing-d3-lib
npm install d3@6.7.0 --silent
cp /tmp/staffing-d3-lib/node_modules/d3/dist/d3.min.js /root/output/js/d3.v6.min.js

cat > /root/output/staffing-heatmap.html <<'HTML_EOF'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Hospital Staffing Transfer Shift Heatmap</title>
  <style>
    :root {
      --ink: #17202a;
      --muted: #5b6774;
      --panel: rgba(255, 255, 255, 0.94);
      --line: #d9e1e7;
      --accent: #0c6f85;
      --accent-soft: rgba(12, 111, 133, 0.12);
      --shadow: 0 20px 48px rgba(23, 32, 42, 0.14);
      --page-a: #eef6fb;
      --page-b: #f6efe3;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      font-family: "Trebuchet MS", "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(13, 111, 133, 0.18), transparent 28%),
        radial-gradient(circle at bottom right, rgba(203, 121, 47, 0.14), transparent 24%),
        linear-gradient(180deg, var(--page-a), var(--page-b));
      min-height: 100vh;
    }

    .page {
      max-width: 1500px;
      margin: 0 auto;
      padding: 28px 22px 40px;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      gap: 18px;
      margin-bottom: 24px;
    }

    .page-header h1 {
      margin: 0 0 10px;
      font-size: 2rem;
      letter-spacing: 0.02em;
    }

    .page-header p {
      margin: 0;
      max-width: 920px;
      color: var(--muted);
      line-height: 1.55;
    }

    .headline-chip {
      padding: 10px 14px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.72);
      border: 1px solid rgba(23, 32, 42, 0.1);
      color: #22404c;
      font-size: 0.92rem;
      white-space: nowrap;
    }

    .dashboard {
      display: grid;
      grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr);
      gap: 22px;
      align-items: start;
    }

    .panel {
      background: var(--panel);
      border: 1px solid rgba(217, 225, 231, 0.9);
      border-radius: 22px;
      box-shadow: var(--shadow);
      padding: 20px;
      backdrop-filter: blur(6px);
    }

    .panel-header {
      display: flex;
      justify-content: space-between;
      gap: 18px;
      align-items: baseline;
      margin-bottom: 14px;
    }

    .panel-header h2,
    .panel-header h3 {
      margin: 0 0 6px;
      font-size: 1.15rem;
    }

    .panel-header p {
      margin: 0;
      color: var(--muted);
      line-height: 1.45;
      font-size: 0.94rem;
    }

    .selection-chip {
      align-self: flex-start;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(12, 111, 133, 0.1);
      border: 1px solid rgba(12, 111, 133, 0.16);
      color: #0b5362;
      font-weight: 700;
      font-size: 0.88rem;
    }

    .legend-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px 14px;
      margin-bottom: 14px;
    }

    .legend-item {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(245, 248, 250, 0.92);
      border: 1px solid var(--line);
      font-size: 0.92rem;
    }

    .legend-swatch {
      width: 14px;
      height: 14px;
      border-radius: 50%;
      border: 1px solid rgba(23, 32, 42, 0.22);
      flex: 0 0 auto;
    }

    svg {
      width: 100%;
      height: auto;
      display: block;
      border-radius: 18px;
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(242, 246, 248, 0.96));
      border: 1px solid rgba(217, 225, 231, 0.82);
    }

    .axis-label {
      fill: #32414d;
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.03em;
    }

    .tick-label {
      fill: #31424f;
      font-size: 14px;
    }

    .weekday-label {
      cursor: pointer;
      font-weight: 700;
      transition: fill 0.16s ease;
    }

    .weekday-label:hover,
    .weekday-label.active {
      fill: #0b6073;
    }

    .heatmap-cell {
      cursor: pointer;
      stroke: rgba(23, 32, 42, 0.14);
      stroke-width: 1.4px;
      transition: stroke-width 0.14s ease, filter 0.14s ease, opacity 0.14s ease;
    }

    .heatmap-cell:hover {
      stroke: rgba(23, 32, 42, 0.55);
      stroke-width: 2.2px;
    }

    .heatmap-cell.selected {
      stroke: #09242d;
      stroke-width: 3.5px;
      filter: drop-shadow(0 0 10px rgba(12, 111, 133, 0.28));
    }

    .heatmap-cell.row-selected {
      stroke: rgba(9, 36, 45, 0.85);
      stroke-width: 2.3px;
    }

    .cell-value {
      fill: #12212b;
      font-size: 14px;
      font-weight: 700;
      text-anchor: middle;
      dominant-baseline: middle;
      pointer-events: none;
    }

    .grid-line,
    .axis-path {
      stroke: rgba(91, 103, 116, 0.3);
      stroke-width: 1px;
    }

    .trend-line {
      fill: none;
      stroke-width: 3px;
      stroke-linecap: round;
      stroke-linejoin: round;
    }

    .trend-point {
      stroke: white;
      stroke-width: 1.6px;
    }

    .detail-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-top: 16px;
    }

    .detail-card {
      background: rgba(250, 252, 253, 0.92);
      border: 1px solid rgba(217, 225, 231, 0.92);
      border-radius: 16px;
      padding: 12px 14px;
    }

    .detail-card h4 {
      margin: 0 0 8px;
      font-size: 0.95rem;
    }

    .detail-card p {
      margin: 4px 0 0;
      color: var(--muted);
      font-size: 0.88rem;
      line-height: 1.45;
    }

    .tooltip {
      position: fixed;
      z-index: 20;
      max-width: 320px;
      padding: 12px 14px;
      border-radius: 14px;
      background: rgba(10, 24, 30, 0.94);
      color: #f4fbff;
      font-size: 0.9rem;
      line-height: 1.48;
      box-shadow: 0 14px 34px rgba(10, 24, 30, 0.28);
      pointer-events: none;
      opacity: 0;
      transform: translateY(8px);
      transition: opacity 0.14s ease, transform 0.14s ease;
    }

    .tooltip.visible {
      opacity: 1;
      transform: translateY(0);
    }

    .tooltip strong {
      display: block;
      margin-bottom: 6px;
      font-size: 0.98rem;
    }

    .footnote {
      margin-top: 14px;
      color: var(--muted);
      font-size: 0.85rem;
      line-height: 1.45;
    }

    @media (max-width: 1080px) {
      .dashboard {
        grid-template-columns: 1fr;
      }

      .page-header {
        flex-direction: column;
        align-items: flex-start;
      }
    }

    @media (max-width: 680px) {
      .page {
        padding: 18px 14px 28px;
      }

      .detail-grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="page">
    <div class="page-header">
      <div>
        <h1>Hospital Staffing Transfer Shift Heatmap</h1>
        <p>Review weekday shift pressure on the left, then inspect how the staffing gap changes by unit and hour on the right. Click a single cell for one shift or click a weekday label to switch into a full-day overview.</p>
      </div>
      <div class="headline-chip">21 shift cells • 4 care units • hourly detail</div>
    </div>

    <div class="dashboard">
      <section class="panel">
        <div class="panel-header">
          <div>
            <h2>Weekday-by-Shift Staffing Gap</h2>
            <p>Color encodes the average staffing gap. Hover for detail, click a cell for a shift view, or click a weekday label for the day overview.</p>
          </div>
        </div>
        <div class="legend-row" id="heat-legend"></div>
        <svg id="heatmap" viewBox="0 0 760 470" aria-label="Staffing gap heatmap"></svg>
        <p class="footnote">Average gap values are shown inside each cell and are based on the local staffing extracts copied into the output folder.</p>
      </section>

      <section class="panel">
        <div class="panel-header">
          <div>
            <h3 id="trend-title">Monday • Day Shift</h3>
            <p id="trend-subtitle">Unit-level hourly staffing gaps for the selected shift.</p>
          </div>
          <div class="selection-chip" id="selection-chip">Shift view</div>
        </div>
        <div class="legend-row" id="unit-legend"></div>
        <svg id="trend-chart" viewBox="0 0 760 440" aria-label="Unit staffing gap trend"></svg>
        <div class="detail-grid" id="detail-grid"></div>
      </section>
    </div>
  </div>

  <div class="tooltip" id="tooltip"></div>

  <script src="js/d3.v6.min.js"></script>
  <script>
    const heatmapSvg = d3.select('#heatmap');
    const trendSvg = d3.select('#trend-chart');
    const tooltip = d3.select('#tooltip');
    const titleNode = d3.select('#trend-title');
    const subtitleNode = d3.select('#trend-subtitle');
    const selectionChip = d3.select('#selection-chip');
    const detailGrid = d3.select('#detail-grid');
    const unitLegend = d3.select('#unit-legend');
    const heatLegend = d3.select('#heat-legend');

    const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    const shifts = ['Night', 'Day', 'Evening'];
    const units = ['Emergency', 'ICU', 'Surgery', 'Pediatrics'];
    const rowHours = [0, 1, 2, 3, 8, 9, 10, 11, 16, 17, 18, 19];

    const unitColor = d3.scaleOrdinal()
      .domain(units)
      .range(['#cb6d2f', '#1d7887', '#5978b9', '#7a9d4b']);

    const state = {
      mode: 'cell',
      weekday: 'Monday',
      shift: 'Day'
    };

    Promise.all([
      d3.csv('data/staffing_heatmap.csv', d => ({
        weekday: d.weekday,
        weekday_order: +d.weekday_order,
        shift: d.shift,
        shift_order: +d.shift_order,
        average_gap: +d.average_gap,
        peak_hour: d.peak_hour,
        peak_gap: +d.peak_gap,
        total_required_staff: +d.total_required_staff,
        total_scheduled_staff: +d.total_scheduled_staff,
        units_above_gap_4: d.units_above_gap_4 ? d.units_above_gap_4.split('|') : []
      })),
      d3.csv('data/unit_hourly_gaps.csv', d => ({
        weekday: d.weekday,
        weekday_order: +d.weekday_order,
        shift: d.shift,
        shift_order: +d.shift_order,
        hour: +d.hour,
        hour_label: d.hour_label,
        unit: d.unit,
        required_staff: +d.required_staff,
        scheduled_staff: +d.scheduled_staff,
        staffing_gap: +d.staffing_gap
      }))
    ]).then(([heatmapData, trendData]) => {
      const heatmapLookup = new Map(heatmapData.map(d => [`${d.weekday}|${d.shift}`, d]));
      const colorScale = d3.scaleLinear()
        .domain(d3.extent(heatmapData, d => d.average_gap))
        .range(['#d7ecf1', '#0b6073']);

      renderHeatLegend(colorScale);
      renderUnitLegend();
      renderHeatmap(heatmapData, colorScale);
      updateTrendChart(trendData, heatmapLookup);

      function renderHeatmap(data, colorScaleRef) {
        const width = 760;
        const height = 470;
        const margin = { top: 56, right: 28, bottom: 28, left: 128 };
        const innerWidth = width - margin.left - margin.right;
        const innerHeight = height - margin.top - margin.bottom;

        const x = d3.scaleBand().domain(shifts).range([0, innerWidth]).padding(0.12);
        const y = d3.scaleBand().domain(weekdays).range([0, innerHeight]).padding(0.12);

        const root = heatmapSvg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

        root.append('text')
          .attr('class', 'axis-label')
          .attr('x', innerWidth / 2)
          .attr('y', -24)
          .attr('text-anchor', 'middle')
          .text('Shift');

        root.append('text')
          .attr('class', 'axis-label')
          .attr('x', -56)
          .attr('y', innerHeight / 2)
          .attr('text-anchor', 'middle')
          .attr('transform', `rotate(-90, -56, ${innerHeight / 2})`)
          .text('Weekday');

        root.selectAll('.shift-label')
          .data(shifts)
          .enter()
          .append('text')
          .attr('class', 'tick-label')
          .attr('x', d => x(d) + x.bandwidth() / 2)
          .attr('y', -8)
          .attr('text-anchor', 'middle')
          .text(d => d);

        root.selectAll('.weekday-label')
          .data(weekdays)
          .enter()
          .append('text')
          .attr('class', 'tick-label weekday-label')
          .attr('data-weekday', d => d)
          .attr('x', -16)
          .attr('y', d => y(d) + y.bandwidth() / 2)
          .attr('text-anchor', 'end')
          .attr('dominant-baseline', 'middle')
          .text(d => d)
          .on('click', (_, weekday) => {
            state.mode = 'row';
            state.weekday = weekday;
            updateSelectionClasses();
            updateTrendChart(trendData, heatmapLookup);
          });

        const cellGroups = root.selectAll('.heatmap-group')
          .data(data)
          .enter()
          .append('g')
          .attr('transform', d => `translate(${x(d.shift)},${y(d.weekday)})`);

        cellGroups.append('rect')
          .attr('class', 'heatmap-cell')
          .attr('data-weekday', d => d.weekday)
          .attr('data-shift', d => d.shift)
          .attr('width', x.bandwidth())
          .attr('height', y.bandwidth())
          .attr('rx', 16)
          .attr('fill', d => colorScaleRef(d.average_gap))
          .on('mousemove', (event, d) => showTooltip(event, d))
          .on('mouseout', hideTooltip)
          .on('click', (_, d) => {
            state.mode = 'cell';
            state.weekday = d.weekday;
            state.shift = d.shift;
            updateSelectionClasses();
            updateTrendChart(trendData, heatmapLookup);
          });

        cellGroups.append('text')
          .attr('class', 'cell-value')
          .attr('x', x.bandwidth() / 2)
          .attr('y', y.bandwidth() / 2)
          .text(d => d.average_gap.toFixed(2));

        updateSelectionClasses();
      }

      function updateSelectionClasses() {
        d3.selectAll('.heatmap-cell')
          .classed('selected', d => state.mode === 'cell' && d.weekday === state.weekday && d.shift === state.shift)
          .classed('row-selected', d => state.mode === 'row' && d.weekday === state.weekday);

        d3.selectAll('.weekday-label')
          .classed('active', d => state.mode === 'row' && d === state.weekday);
      }

      function updateTrendChart(trendRows, lookup) {
        const width = 760;
        const height = 440;
        const margin = { top: 28, right: 24, bottom: 56, left: 64 };
        const innerWidth = width - margin.left - margin.right;
        const innerHeight = height - margin.top - margin.bottom;

        const scopedRows = trendRows.filter(d => {
          if (state.mode === 'cell') {
            return d.weekday === state.weekday && d.shift === state.shift;
          }
          return d.weekday === state.weekday;
        });

        const hours = state.mode === 'cell'
          ? Array.from(new Set(scopedRows.map(d => d.hour))).sort((a, b) => a - b)
          : rowHours;

        const hourLabels = new Map(scopedRows.map(d => [d.hour, d.hour_label]));
        const grouped = units.map(unit => ({
          unit,
          values: scopedRows
            .filter(d => d.unit === unit)
            .sort((a, b) => a.hour - b.hour)
        }));

        const x = d3.scalePoint()
          .domain(hours)
          .range([0, innerWidth])
          .padding(0.45);

        const y = d3.scaleLinear()
          .domain([0, d3.max(scopedRows, d => d.staffing_gap) + 1])
          .nice()
          .range([innerHeight, 0]);

        trendSvg.selectAll('*').remove();
        const root = trendSvg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

        root.append('g')
          .selectAll('line')
          .data(y.ticks(5))
          .enter()
          .append('line')
          .attr('class', 'grid-line')
          .attr('x1', 0)
          .attr('x2', innerWidth)
          .attr('y1', d => y(d))
          .attr('y2', d => y(d));

        root.append('g')
          .attr('transform', `translate(0,${innerHeight})`)
          .call(d3.axisBottom(x).tickFormat(d => hourLabels.get(d) || d))
          .call(g => g.selectAll('text').attr('class', 'tick-label').attr('transform', 'rotate(-20)').style('text-anchor', 'end'))
          .call(g => g.select('.domain').attr('class', 'axis-path'));

        root.append('g')
          .call(d3.axisLeft(y).ticks(5))
          .call(g => g.selectAll('text').attr('class', 'tick-label'))
          .call(g => g.select('.domain').attr('class', 'axis-path'));

        root.append('text')
          .attr('class', 'axis-label')
          .attr('x', innerWidth / 2)
          .attr('y', innerHeight + 48)
          .attr('text-anchor', 'middle')
          .text('Hour');

        root.append('text')
          .attr('class', 'axis-label')
          .attr('x', -42)
          .attr('y', innerHeight / 2)
          .attr('text-anchor', 'middle')
          .attr('transform', `rotate(-90, -42, ${innerHeight / 2})`)
          .text('Staffing Gap');

        const line = d3.line()
          .x(d => x(d.hour))
          .y(d => y(d.staffing_gap));

        const lineGroup = root.selectAll('.trend-group')
          .data(grouped)
          .enter()
          .append('g')
          .attr('class', 'trend-group')
          .attr('data-unit', d => d.unit);

        lineGroup.append('path')
          .attr('class', 'trend-line')
          .attr('data-unit', d => d.unit)
          .attr('stroke', d => unitColor(d.unit))
          .attr('d', d => line(d.values));

        lineGroup.selectAll('.trend-point')
          .data(d => d.values.map(value => ({ ...value, unit: d.unit })))
          .enter()
          .append('circle')
          .attr('class', 'trend-point')
          .attr('data-unit', d => d.unit)
          .attr('cx', d => x(d.hour))
          .attr('cy', d => y(d.staffing_gap))
          .attr('r', 5)
          .attr('fill', d => unitColor(d.unit));

        updateDetailCards(grouped, scopedRows, lookup);
      }

      function updateDetailCards(grouped, scopedRows, lookup) {
        let titleText;
        let subtitleText;

        if (state.mode === 'cell') {
          const selectedCell = lookup.get(`${state.weekday}|${state.shift}`);
          titleText = `${state.weekday} • ${state.shift} Shift`;
          subtitleText = `Unit-level hourly staffing gaps for the selected shift. Peak hour: ${selectedCell.peak_hour} (${selectedCell.peak_gap.toFixed(1)} gap).`;
          selectionChip.text('Shift view');
        } else {
          titleText = `${state.weekday} • Day Overview`;
          subtitleText = `Unit-level hourly staffing gaps across every shift on ${state.weekday}.`;
          selectionChip.text('Day overview');
        }

        titleNode.text(titleText);
        subtitleNode.text(subtitleText);

        const cards = grouped.map(group => {
          const avgGap = d3.mean(group.values, d => d.staffing_gap);
          const peak = d3.max(group.values, d => d.staffing_gap);
          const peakRow = group.values.find(d => d.staffing_gap === peak);
          return {
            unit: group.unit,
            avgGap,
            peak,
            peakHour: peakRow ? peakRow.hour_label : '',
            totalRequired: d3.sum(group.values, d => d.required_staff),
            totalScheduled: d3.sum(group.values, d => d.scheduled_staff)
          };
        });

        detailGrid.selectAll('*').remove();

        const cardSelection = detailGrid.selectAll('.detail-card')
          .data(cards)
          .enter()
          .append('div')
          .attr('class', 'detail-card')
          .attr('data-unit-card', d => d.unit);

        cardSelection.append('h4')
          .text(d => d.unit);

        cardSelection.append('p')
          .html(d => `Average gap: <strong>${d.avgGap.toFixed(2)}</strong><br>Peak hour: <strong>${d.peakHour}</strong> (${d.peak.toFixed(1)})<br>Required vs scheduled: <strong>${d.totalRequired}</strong> / <strong>${d.totalScheduled}</strong>`);
      }

      function renderUnitLegend() {
        unitLegend.selectAll('.legend-item')
          .data(units)
          .enter()
          .append('div')
          .attr('class', 'legend-item')
          .html(d => `<span class="legend-swatch" style="background:${unitColor(d)}"></span>${d}`);
      }

      function renderHeatLegend(colorScaleRef) {
        const values = d3.range(5).map(index => {
          const min = colorScaleRef.domain()[0];
          const max = colorScaleRef.domain()[1];
          return min + (index / 4) * (max - min);
        });

        heatLegend.selectAll('.legend-item')
          .data(values)
          .enter()
          .append('div')
          .attr('class', 'legend-item')
          .html(d => `<span class="legend-swatch" style="background:${colorScaleRef(d)}"></span>${d.toFixed(2)} avg gap`);
      }

      function showTooltip(event, d) {
        tooltip
          .classed('visible', true)
          .html([
            `<strong>${d.weekday} • ${d.shift} Shift</strong>`,
            `Average gap: ${d.average_gap.toFixed(2)}`,
            `Peak hour: ${d.peak_hour}`,
            `Peak gap: ${d.peak_gap.toFixed(1)}`,
            `Required staff total: ${d.total_required_staff}`,
            `Scheduled staff total: ${d.total_scheduled_staff}`,
            `Units above 4: ${d.units_above_gap_4.join(', ')}`
          ].join('<br>'))
          .style('left', `${event.clientX + 14}px`)
          .style('top', `${event.clientY - 12}px`);
      }

      function hideTooltip() {
        tooltip.classed('visible', false);
      }
    });
  </script>
</body>
</html>
HTML_EOF
