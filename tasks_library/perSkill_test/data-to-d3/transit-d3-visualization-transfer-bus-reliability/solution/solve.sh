#!/bin/bash
set -euo pipefail

OUTPUT_DIR="/root/output"
ASSET_DIR="${OUTPUT_DIR}/assets"

mkdir -p "${ASSET_DIR}"
cp /root/data/route_performance.csv "${ASSET_DIR}/route_performance.csv"
cp /root/data/stop_delays.csv "${ASSET_DIR}/stop_delays.csv"

cp /opt/d3/node_modules/d3/dist/d3.min.js "${ASSET_DIR}/d3.v7.min.js"

cat > "${OUTPUT_DIR}/bus-reliability.html" <<'HTML'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Bus Reliability Small Multiples</title>
  <link rel="stylesheet" href="assets/styles.css">
</head>
<body>
  <main class="page-shell">
    <header class="hero">
      <p class="eyebrow">Transit Operations Snapshot</p>
      <h1>Bus Reliability Through the Day</h1>
      <p class="subtitle">Compare route on-time performance by time bin and inspect the stops that drive delays.</p>
    </header>

    <section class="toolbar">
      <div class="section-label">Routes</div>
      <div id="route-selector" class="route-selector" aria-label="Route selector"></div>
    </section>

    <section class="overview-grid">
      <div class="chart-card">
        <div class="card-header">
          <div>
            <h2>On-Time Rate Small Multiples</h2>
            <p class="card-copy">Each panel uses the same 0% to 100% scale for direct comparison.</p>
          </div>
          <div id="focus-readout" class="focus-readout"></div>
        </div>
        <svg id="reliability-small-multiples" viewBox="0 0 980 620" role="img" aria-label="Bus route reliability small multiples"></svg>
      </div>

      <aside class="detail-column">
        <section class="summary-card">
          <h2>Selected Scope</h2>
          <div id="interval-summary" class="summary-grid"></div>
        </section>

        <section class="table-card">
          <div class="table-header">
            <h2>Worst-Performing Stops</h2>
            <p id="table-scope-label" class="table-scope-label"></p>
          </div>
          <table id="stop-detail-table">
            <thead>
              <tr>
                <th>Stop</th>
                <th>Late arrivals</th>
                <th>10+ min delays</th>
                <th>Arrivals</th>
                <th>Late rate</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </section>
      </aside>
    </section>
  </main>

  <script src="assets/d3.v7.min.js"></script>
  <script src="assets/app.js"></script>
</body>
</html>
HTML

cat > "${ASSET_DIR}/styles.css" <<'CSS'
:root {
  --bg: #f3efe6;
  --card: #fffaf2;
  --ink: #172126;
  --muted: #55636d;
  --line: #274c77;
  --line-alt: #6ea4bf;
  --accent: #b65f3c;
  --accent-soft: #f3d9cd;
  --border: #d6c8b8;
  --grid: #ded6ca;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
  color: var(--ink);
  background:
    radial-gradient(circle at top left, rgba(182, 95, 60, 0.12), transparent 32%),
    linear-gradient(180deg, #f9f5ee 0%, var(--bg) 100%);
}

.page-shell {
  max-width: 1280px;
  margin: 0 auto;
  padding: 32px 20px 40px;
}

.hero {
  margin-bottom: 24px;
}

.eyebrow {
  margin: 0 0 8px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-size: 0.78rem;
  color: var(--accent);
  font-weight: 700;
}

h1,
h2,
p {
  margin: 0;
}

h1 {
  font-size: clamp(2rem, 3vw, 3rem);
  line-height: 1.05;
}

.subtitle,
.card-copy,
.table-scope-label {
  color: var(--muted);
}

.subtitle {
  margin-top: 10px;
  max-width: 760px;
  line-height: 1.5;
}

.toolbar {
  margin-bottom: 18px;
}

.section-label {
  margin-bottom: 10px;
  color: var(--muted);
  font-size: 0.9rem;
  font-weight: 700;
}

.route-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.route-chip {
  border: 1px solid var(--border);
  background: rgba(255, 250, 242, 0.9);
  color: var(--ink);
  border-radius: 999px;
  padding: 10px 14px;
  font-size: 0.95rem;
  cursor: pointer;
  transition: background-color 0.16s ease, border-color 0.16s ease, transform 0.16s ease;
}

.route-chip:hover {
  transform: translateY(-1px);
}

.route-chip[aria-pressed="true"] {
  background: var(--accent);
  border-color: var(--accent);
  color: #fffaf2;
}

.overview-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(320px, 0.95fr);
  gap: 18px;
  align-items: start;
}

.chart-card,
.summary-card,
.table-card {
  background: var(--card);
  border: 1px solid rgba(214, 200, 184, 0.85);
  border-radius: 20px;
  box-shadow: 0 18px 40px rgba(23, 33, 38, 0.08);
}

.chart-card {
  padding: 18px 18px 12px;
}

.detail-column {
  display: grid;
  gap: 18px;
}

.summary-card,
.table-card {
  padding: 18px;
}

.card-header,
.table-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 12px;
}

.focus-readout {
  min-width: 180px;
  padding: 10px 12px;
  border-radius: 14px;
  background: var(--accent-soft);
  color: #5d2f1f;
  font-size: 0.92rem;
  line-height: 1.35;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  background: rgba(39, 76, 119, 0.08);
  border-radius: 14px;
  padding: 12px;
}

.metric-label {
  display: block;
  color: var(--muted);
  font-size: 0.82rem;
  margin-bottom: 6px;
}

.metric-value {
  display: block;
  font-size: 1.3rem;
  font-weight: 700;
}

#stop-detail-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.94rem;
}

#stop-detail-table th,
#stop-detail-table td {
  padding: 10px 8px;
  border-bottom: 1px solid rgba(214, 200, 184, 0.8);
  text-align: left;
}

#stop-detail-table thead th {
  color: var(--muted);
  font-weight: 700;
  font-size: 0.84rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

#stop-detail-table tbody tr:last-child td {
  border-bottom: none;
}

#stop-detail-table tbody tr:nth-child(odd) {
  background: rgba(243, 239, 230, 0.55);
}

.panel-bg {
  fill: rgba(255, 255, 255, 0.55);
  stroke: var(--border);
  stroke-width: 1.2;
  rx: 18px;
  ry: 18px;
}

.route-panel[data-selected="true"] .panel-bg {
  stroke: var(--accent);
  stroke-width: 2;
}

.panel-title {
  fill: var(--ink);
  font-size: 13px;
  font-weight: 700;
}

.panel-subtitle {
  fill: var(--muted);
  font-size: 11px;
}

.panel-axis path,
.panel-axis line {
  stroke: var(--grid);
}

.panel-axis text {
  fill: var(--muted);
  font-size: 10px;
}

.guide-line {
  stroke: var(--grid);
  stroke-dasharray: 4 4;
}

.reliability-line {
  fill: none;
  stroke: var(--line);
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.route-panel[data-selected="true"] .reliability-line {
  stroke: var(--accent);
}

.time-point {
  fill: var(--line-alt);
  stroke: #fffaf2;
  stroke-width: 1.5;
}

.route-panel[data-selected="true"] .time-point {
  fill: var(--accent);
}

.focus-band {
  fill: transparent;
  cursor: crosshair;
}

.focus-band[aria-current="true"] {
  fill: rgba(182, 95, 60, 0.18);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 980px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .page-shell {
    padding: 20px 14px 32px;
  }

  .card-header,
  .table-header {
    flex-direction: column;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }
}
CSS

cat > "${ASSET_DIR}/app.js" <<'JS'
const rateFormatter = d3.format(".1%");
const integerFormatter = d3.format(",");

const state = {
  selectedRouteId: null,
  activeTimeBin: null,
  routeSummaries: [],
  routeSeries: [],
  stopRows: [],
  timeBins: []
};

Promise.all([
  d3.csv("assets/route_performance.csv", (row) => ({
    route_id: row.route_id,
    route_name: row.route_name,
    time_bin: row.time_bin,
    scheduled_trips: +row.scheduled_trips,
    on_time_trips: +row.on_time_trips
  })),
  d3.csv("assets/stop_delays.csv", (row) => ({
    route_id: row.route_id,
    stop_id: row.stop_id,
    stop_name: row.stop_name,
    time_bin: row.time_bin,
    total_arrivals: +row.total_arrivals,
    late_arrivals: +row.late_arrivals,
    delays_over_10_min: +row.delays_over_10_min
  }))
]).then(([routeRows, stopRows]) => {
  state.stopRows = stopRows;
  state.timeBins = Array.from(new Set(routeRows.map((row) => row.time_bin))).sort(d3.ascending);

  const grouped = d3.groups(routeRows, (row) => row.route_id).map(([routeId, rows]) => {
    rows.sort((left, right) => d3.ascending(left.time_bin, right.time_bin));
    const scheduled = d3.sum(rows, (row) => row.scheduled_trips);
    const onTime = d3.sum(rows, (row) => row.on_time_trips);
    return {
      route_id: routeId,
      route_name: rows[0].route_name,
      scheduled_trips: scheduled,
      on_time_trips: onTime,
      late_trips: scheduled - onTime,
      all_day_rate: onTime / scheduled,
      points: rows.map((row) => ({
        ...row,
        on_time_rate: row.on_time_trips / row.scheduled_trips,
        late_trips: row.scheduled_trips - row.on_time_trips
      }))
    };
  }).sort((left, right) => d3.ascending(left.all_day_rate, right.all_day_rate) || d3.ascending(left.route_id, right.route_id));

  state.routeSummaries = grouped;
  state.routeSeries = grouped;
  state.selectedRouteId = grouped[0].route_id;

  renderRouteSelector();
  renderSmallMultiples();
  syncView();
}).catch((error) => {
  console.error(error);
});

function renderRouteSelector() {
  const selector = d3.select("#route-selector");
  selector.selectAll("button.route-chip")
    .data(state.routeSummaries, (d) => d.route_id)
    .join("button")
    .attr("type", "button")
    .attr("class", "route-chip")
    .attr("data-route-id", (d) => d.route_id)
    .attr("aria-pressed", (d) => (d.route_id === state.selectedRouteId ? "true" : "false"))
    .text((d) => `${d.route_name} · ${rateFormatter(d.all_day_rate)}`)
    .on("click", (_, d) => {
      state.selectedRouteId = d.route_id;
      state.activeTimeBin = null;
      syncView();
    });
}

function renderSmallMultiples() {
  const svg = d3.select("#reliability-small-multiples");
  const width = 980;
  const height = 620;
  const cols = 2;
  const panelWidth = 450;
  const panelHeight = 250;
  const gapX = 32;
  const gapY = 28;
  const offsetX = 28;
  const offsetY = 24;
  const innerMargin = { top: 34, right: 18, bottom: 34, left: 42 };
  const innerWidth = panelWidth - innerMargin.left - innerMargin.right;
  const innerHeight = panelHeight - innerMargin.top - innerMargin.bottom;

  svg.attr("viewBox", `0 0 ${width} ${height}`);

  const yScale = d3.scaleLinear().domain([0, 1]).range([innerHeight, 0]);
  const xScale = d3.scaleBand().domain(state.timeBins).range([0, innerWidth]).padding(0.16);
  const yTicks = [0, 0.5, 1];
  const yAxis = d3.axisLeft(yScale).tickValues(yTicks).tickFormat(d3.format(".0%"));
  const xAxis = d3.axisBottom(xScale).tickSizeOuter(0);
  const line = d3.line()
    .x((d) => xScale(d.time_bin) + xScale.bandwidth() / 2)
    .y((d) => yScale(d.on_time_rate));

  const panels = svg.selectAll("g.route-panel")
    .data(state.routeSeries, (d) => d.route_id)
    .join((enter) => {
      const panel = enter.append("g").attr("class", "route-panel");
      panel.append("rect").attr("class", "panel-bg").attr("width", panelWidth).attr("height", panelHeight);
      panel.append("text").attr("class", "panel-title").attr("x", 16).attr("y", 22);
      panel.append("text").attr("class", "panel-subtitle").attr("x", 16).attr("y", 40);
      const inner = panel.append("g").attr("class", "panel-inner").attr("transform", `translate(${innerMargin.left},${innerMargin.top})`);
      inner.append("g").attr("class", "panel-axis axis-y");
      inner.append("g").attr("class", "panel-axis axis-x").attr("transform", `translate(0,${innerHeight})`);
      inner.selectAll("line.guide-line")
        .data(yTicks)
        .join("line")
        .attr("class", "guide-line")
        .attr("x1", 0)
        .attr("x2", innerWidth)
        .attr("y1", (d) => yScale(d))
        .attr("y2", (d) => yScale(d));
      inner.append("path").attr("class", "reliability-line");
      inner.append("g").attr("class", "point-layer");
      inner.append("g").attr("class", "band-layer");
      return panel;
    });

  panels
    .attr("data-route-id", (d) => d.route_id)
    .attr("transform", (_, index) => {
      const col = index % cols;
      const row = Math.floor(index / cols);
      const x = offsetX + col * (panelWidth + gapX);
      const y = offsetY + row * (panelHeight + gapY);
      return `translate(${x},${y})`;
    });

  panels.select(".panel-title").text((d) => d.route_name);
  panels.select(".panel-subtitle").text((d) => `${rateFormatter(d.all_day_rate)} all-day on time`);

  panels.each(function(panelDatum) {
    const panel = d3.select(this);
    const inner = panel.select(".panel-inner");
    inner.select(".axis-y").call(yAxis);
    inner.select(".axis-x").call(xAxis);
    inner.select(".reliability-line")
      .attr("data-route-id", panelDatum.route_id)
      .attr("d", line(panelDatum.points));

    inner.select(".point-layer")
      .selectAll("circle.time-point")
      .data(panelDatum.points, (d) => `${d.route_id}-${d.time_bin}`)
      .join("circle")
      .attr("class", "time-point")
      .attr("r", 5)
      .attr("cx", (d) => xScale(d.time_bin) + xScale.bandwidth() / 2)
      .attr("cy", (d) => yScale(d.on_time_rate))
      .attr("data-route-id", (d) => d.route_id)
      .attr("data-time-bin", (d) => d.time_bin)
      .attr("data-on-time-rate", (d) => d.on_time_rate.toFixed(4))
      .attr("data-late-trips", (d) => String(d.late_trips));

    inner.select(".band-layer")
      .selectAll("rect.focus-band")
      .data(panelDatum.points, (d) => `${d.route_id}-${d.time_bin}`)
      .join("rect")
      .attr("class", "focus-band")
      .attr("x", (d) => xScale(d.time_bin))
      .attr("y", 0)
      .attr("width", xScale.bandwidth())
      .attr("height", innerHeight)
      .attr("data-route-id", (d) => d.route_id)
      .attr("data-time-bin", (d) => d.time_bin)
      .attr("aria-current", "false")
      .on("mouseenter", (_, d) => {
        if (d.route_id !== state.selectedRouteId) {
          return;
        }
        state.activeTimeBin = d.time_bin;
        syncView();
      });

    panel.on("mouseleave", () => {
      if (panelDatum.route_id !== state.selectedRouteId || state.activeTimeBin === null) {
        return;
      }
      state.activeTimeBin = null;
      syncView();
    });
  });
}

function syncView() {
  const selectedRoute = getSelectedRoute();
  const selectedInterval = getSelectedInterval();
  const scopeLabel = state.activeTimeBin === null ? "All day" : state.activeTimeBin;

  d3.selectAll("button.route-chip")
    .attr("aria-pressed", (d) => (d.route_id === state.selectedRouteId ? "true" : "false"));

  d3.selectAll("g.route-panel")
    .attr("data-selected", (d) => (d.route_id === state.selectedRouteId ? "true" : "false"));

  d3.selectAll("rect.focus-band")
    .attr("aria-current", (d) => (d.route_id === state.selectedRouteId && d.time_bin === state.activeTimeBin ? "true" : "false"));

  d3.select("#focus-readout").html(`
    <strong>${selectedRoute.route_name}</strong><br>
    ${scopeLabel}
  `);

  renderSummary(selectedRoute, selectedInterval, scopeLabel);
  renderTable(selectedRoute, scopeLabel);
}

function renderSummary(routeSummary, intervalSummary, scopeLabel) {
  const metrics = [
    { label: "Scope", value: scopeLabel },
    { label: "On-time rate", value: rateFormatter(intervalSummary.on_time_rate) },
    { label: "Late trips", value: integerFormatter(intervalSummary.late_trips) },
    { label: "Scheduled trips", value: integerFormatter(intervalSummary.scheduled_trips) }
  ];

  d3.select("#interval-summary")
    .selectAll("div.metric-card")
    .data(metrics)
    .join("div")
    .attr("class", "metric-card")
    .html((d) => `<span class="metric-label">${d.label}</span><span class="metric-value">${d.value}</span>`);

  d3.select("#table-scope-label")
    .text(`${routeSummary.route_name} · ${scopeLabel}`);
}

function renderTable(routeSummary, scopeLabel) {
  const rows = aggregateStops(routeSummary.route_id, state.activeTimeBin).slice(0, 5);
  const scopeAttr = state.activeTimeBin === null ? "all-day" : state.activeTimeBin;
  const tbody = d3.select("#stop-detail-table tbody");

  const tableRows = tbody.selectAll("tr")
    .data(rows, (d) => d.stop_id)
    .join("tr")
    .attr("data-route-id", routeSummary.route_id)
    .attr("data-stop-id", (d) => d.stop_id)
    .attr("data-scope", scopeAttr);

  tableRows.selectAll("td")
    .data((d) => [
      d.stop_name,
      integerFormatter(d.late_arrivals),
      integerFormatter(d.delays_over_10_min),
      integerFormatter(d.total_arrivals),
      rateFormatter(d.late_arrivals / d.total_arrivals)
    ])
    .join("td")
    .text((d) => d);
}

function aggregateStops(routeId, timeBin) {
  const totals = new Map();

  state.stopRows.forEach((row) => {
    if (row.route_id !== routeId) {
      return;
    }
    if (timeBin !== null && row.time_bin !== timeBin) {
      return;
    }
    if (!totals.has(row.stop_id)) {
      totals.set(row.stop_id, {
        stop_id: row.stop_id,
        stop_name: row.stop_name,
        late_arrivals: 0,
        delays_over_10_min: 0,
        total_arrivals: 0
      });
    }
    const entry = totals.get(row.stop_id);
    entry.late_arrivals += row.late_arrivals;
    entry.delays_over_10_min += row.delays_over_10_min;
    entry.total_arrivals += row.total_arrivals;
  });

  return Array.from(totals.values()).sort((left, right) =>
    d3.descending(left.delays_over_10_min, right.delays_over_10_min) ||
    d3.descending(left.late_arrivals, right.late_arrivals) ||
    d3.ascending(left.stop_id, right.stop_id)
  );
}

function getSelectedRoute() {
  return state.routeSummaries.find((route) => route.route_id === state.selectedRouteId);
}

function getSelectedInterval() {
  const routeSummary = getSelectedRoute();
  if (state.activeTimeBin === null) {
    return {
      scheduled_trips: routeSummary.scheduled_trips,
      on_time_trips: routeSummary.on_time_trips,
      late_trips: routeSummary.late_trips,
      on_time_rate: routeSummary.all_day_rate
    };
  }
  const point = routeSummary.points.find((item) => item.time_bin === state.activeTimeBin);
  return {
    scheduled_trips: point.scheduled_trips,
    on_time_trips: point.on_time_trips,
    late_trips: point.late_trips,
    on_time_rate: point.on_time_rate
  };
}
JS
