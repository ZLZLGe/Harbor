#!/bin/bash
set -euo pipefail

mkdir -p /root/output/js /root/output/data
cp /root/data/county_outages.csv /root/output/data/county_outages.csv
cp /root/data/county_boundaries.geojson /root/output/data/county_boundaries.geojson

mkdir -p /tmp/outage-atlas-d3
cd /tmp/outage-atlas-d3
npm install d3@6.7.0 --silent
cp /tmp/outage-atlas-d3/node_modules/d3/dist/d3.min.js /root/output/js/d3.v6.min.js

cat > /root/output/outage-atlas.html <<'HTML_EOF'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>County Outages Transfer Choropleth Atlas</title>
  <style>
    :root {
      --ink: #1d2730;
      --muted: #617180;
      --panel: rgba(255, 255, 255, 0.9);
      --line: rgba(73, 94, 112, 0.18);
      --accent: #8c2f39;
      --shadow: 0 20px 48px rgba(26, 38, 49, 0.12);
      --selected: #13202b;
      --bg-top: #f2f0e9;
      --bg-bottom: #eef4f9;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      font-family: "Avenir Next", "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(140, 47, 57, 0.12), transparent 28%),
        radial-gradient(circle at top right, rgba(72, 120, 161, 0.13), transparent 30%),
        linear-gradient(180deg, var(--bg-top), var(--bg-bottom));
      min-height: 100vh;
    }

    .page {
      max-width: 1500px;
      margin: 0 auto;
      padding: 28px 22px 36px;
    }

    h1 {
      margin: 0 0 8px;
      font-size: 2.2rem;
      letter-spacing: 0.02em;
    }

    .subtitle {
      margin: 0 0 24px;
      max-width: 940px;
      color: var(--muted);
      line-height: 1.55;
      font-size: 1rem;
    }

    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1.2fr) minmax(360px, 0.95fr);
      gap: 22px;
      align-items: start;
    }

    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px 18px 20px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(5px);
    }

    .panel-header {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: baseline;
      margin-bottom: 14px;
    }

    .panel-header h2 {
      margin: 0;
      font-size: 1.18rem;
    }

    .panel-header p {
      margin: 0;
      color: var(--muted);
      font-size: 0.93rem;
    }

    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 14px;
    }

    .legend-item {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(246, 248, 249, 0.92);
      border: 1px solid var(--line);
      font-size: 0.88rem;
    }

    .legend-swatch {
      width: 14px;
      height: 14px;
      border-radius: 4px;
      border: 1px solid rgba(19, 32, 43, 0.22);
      flex: 0 0 auto;
    }

    svg {
      width: 100%;
      height: auto;
      display: block;
    }

    #map {
      min-height: 620px;
    }

    .county-shape {
      cursor: pointer;
      stroke: rgba(255, 255, 255, 0.88);
      stroke-width: 2px;
      transition: transform 0.12s ease, stroke-width 0.12s ease, filter 0.12s ease, opacity 0.12s ease;
    }

    .county-shape.hovered,
    .county-shape.selected {
      stroke: var(--selected);
      stroke-width: 4px;
      filter: drop-shadow(0 0 10px rgba(19, 32, 43, 0.28));
    }

    .county-label {
      font-size: 11px;
      font-weight: 700;
      text-anchor: middle;
      pointer-events: none;
      fill: rgba(17, 26, 34, 0.86);
    }

    .county-value {
      font-size: 10px;
      text-anchor: middle;
      pointer-events: none;
      fill: rgba(17, 26, 34, 0.68);
    }

    .county-feature:hover .county-shape {
      opacity: 0.95;
    }

    #bars {
      min-height: 520px;
    }

    .bar-group {
      cursor: pointer;
    }

    .rank-bar {
      transition: stroke-width 0.12s ease, filter 0.12s ease, opacity 0.12s ease;
    }

    .bar-group.hovered .rank-bar,
    .bar-group.selected .rank-bar {
      stroke: var(--selected);
      stroke-width: 3px;
      filter: drop-shadow(0 0 8px rgba(19, 32, 43, 0.22));
    }

    .axis text,
    .axis-label {
      fill: var(--muted);
      font-size: 12px;
    }

    .axis path,
    .axis line {
      stroke: rgba(73, 94, 112, 0.28);
    }

    .grid line {
      stroke: rgba(73, 94, 112, 0.16);
      stroke-dasharray: 4 4;
    }

    .grid path {
      stroke: none;
    }

    .detail-panel {
      margin-top: 18px;
      padding: 18px;
      border-radius: 18px;
      background: linear-gradient(180deg, rgba(248, 250, 252, 0.95), rgba(240, 244, 247, 0.98));
      border: 1px solid rgba(73, 94, 112, 0.14);
    }

    .detail-kicker {
      margin: 0 0 8px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 0.76rem;
      color: var(--muted);
    }

    #detail-title {
      margin: 0 0 12px;
      font-size: 1.45rem;
    }

    .detail-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }

    .detail-card {
      border-radius: 14px;
      padding: 12px;
      background: rgba(255, 255, 255, 0.92);
      border: 1px solid rgba(73, 94, 112, 0.12);
    }

    .detail-card span {
      display: block;
      font-size: 0.78rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 6px;
    }

    .detail-card strong {
      font-size: 1.05rem;
      line-height: 1.35;
    }

    .detail-footer {
      margin-top: 12px;
      font-size: 0.92rem;
      color: var(--muted);
    }

    .tooltip {
      position: fixed;
      z-index: 20;
      max-width: 280px;
      padding: 12px 14px;
      border-radius: 12px;
      background: rgba(17, 26, 34, 0.94);
      color: #f8fbfd;
      font-size: 0.9rem;
      line-height: 1.45;
      box-shadow: 0 14px 32px rgba(17, 26, 34, 0.28);
      pointer-events: none;
      opacity: 0;
      transform: translateY(8px);
      transition: opacity 0.14s ease, transform 0.14s ease;
    }

    .tooltip.visible {
      opacity: 1;
      transform: translateY(0);
    }

    @media (max-width: 1080px) {
      .layout {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 720px) {
      .page {
        padding: 20px 14px 28px;
      }

      .detail-grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="page">
    <h1>County Outage Atlas</h1>
    <p class="subtitle">A county-by-county outage severity map linked to a ranked county view so the highest-risk service areas are easy to compare, inspect, and track from the same page.</p>

    <div class="layout">
      <section class="panel">
        <div class="panel-header">
          <h2>Severity Choropleth</h2>
          <p>County fill and rank colors share the same severity scale.</p>
        </div>
        <div id="legend" class="legend" aria-label="Severity legend"></div>
        <svg id="map" viewBox="0 0 760 620" aria-label="County outage severity map"></svg>
      </section>

      <section class="panel">
        <div class="panel-header">
          <h2>Ranked Severity</h2>
          <p>Sorted by severity index from highest to lowest.</p>
        </div>
        <svg id="bars" viewBox="0 0 600 520" aria-label="Ranked county severity chart"></svg>

        <div class="detail-panel" id="details">
          <p class="detail-kicker">Selected County</p>
          <h3 id="detail-title"></h3>
          <div class="detail-grid">
            <div class="detail-card">
              <span>Severity Index</span>
              <strong id="detail-severity"></strong>
            </div>
            <div class="detail-card">
              <span>Customers Out</span>
              <strong id="detail-customers"></strong>
            </div>
            <div class="detail-card">
              <span>Percent Affected</span>
              <strong id="detail-percent"></strong>
            </div>
            <div class="detail-card">
              <span>Restoration ETA</span>
              <strong id="detail-eta"></strong>
            </div>
            <div class="detail-card">
              <span>Critical Facility</span>
              <strong id="detail-facility"></strong>
            </div>
            <div class="detail-card">
              <span>Report Time</span>
              <strong id="detail-reported"></strong>
            </div>
          </div>
          <p class="detail-footer" id="detail-footer"></p>
        </div>
      </section>
    </div>
  </div>

  <div id="tooltip" class="tooltip"></div>

  <script src="js/d3.v6.min.js"></script>
  <script>
    const widthMap = 760;
    const heightMap = 620;
    const widthBars = 600;
    const heightBars = 520;
    const severityBreaks = [20, 40, 60, 80];
    const severityColors = ["#f2e8cf", "#ddb892", "#d88c53", "#a54f37", "#5c1f22"];
    const severityLabels = ["0-19", "20-39", "40-59", "60-79", "80-100"];

    const formatInt = d3.format(",");
    const formatPercent = d3.format(".1%");

    const state = {
      selectedId: null,
      hoveredId: null,
      dataById: new Map(),
      orderedData: []
    };

    const colorScale = d3.scaleThreshold()
      .domain(severityBreaks)
      .range(severityColors);

    const tooltip = d3.select("#tooltip");

    Promise.all([
      d3.json("data/county_boundaries.geojson"),
      d3.csv("data/county_outages.csv", row => ({
        county_fips: row.county_fips,
        county_name: row.county_name,
        customers_out: +row.customers_out,
        total_customers: +row.total_customers,
        severity_index: +row.severity_index,
        restoration_eta_hours: +row.restoration_eta_hours,
        critical_facility: row.critical_facility,
        reported_at: row.reported_at
      }))
    ]).then(([geojson, outages]) => {
      outages.forEach(d => {
        d.percent_affected = d.customers_out / d.total_customers;
        state.dataById.set(d.county_fips, d);
      });

      state.orderedData = outages.slice().sort((a, b) => d3.descending(a.severity_index, b.severity_index));
      state.selectedId = state.orderedData[0].county_fips;

      const mergedFeatures = geojson.features.map(feature => {
        const row = state.dataById.get(feature.properties.county_fips);
        return {
          ...feature,
          properties: {
            ...feature.properties,
            ...row
          }
        };
      });

      renderLegend();
      renderMap(mergedFeatures);
      renderBars(state.orderedData);
      refreshActiveState();
    });

    function renderLegend() {
      const legend = d3.select("#legend");
      legend.selectAll(".legend-item")
        .data(severityLabels.map((label, index) => ({ label, color: severityColors[index] })))
        .enter()
        .append("div")
        .attr("class", "legend-item")
        .html(d => '<span class="legend-swatch" style="background:' + d.color + '"></span><span>' + d.label + '</span>');
    }

    function renderMap(features) {
      const svg = d3.select("#map");
      const projection = d3.geoMercator().fitSize([widthMap - 40, heightMap - 30], {
        type: "FeatureCollection",
        features
      });
      const path = d3.geoPath(projection);
      const group = svg.append("g").attr("transform", "translate(20, 15)");

      const featureGroups = group.selectAll(".county-feature")
        .data(features)
        .enter()
        .append("g")
        .attr("class", "county-feature")
        .attr("data-county", d => d.properties.county_name)
        .attr("data-fips", d => d.properties.county_fips)
        .on("mouseenter", (event, d) => setHovered(d.properties.county_fips, event))
        .on("mousemove", (event, d) => showTooltip(d.properties, event))
        .on("mouseleave", () => clearHovered())
        .on("click", (event, d) => setSelected(d.properties.county_fips, event));

      featureGroups.append("path")
        .attr("class", "county-shape")
        .attr("data-county", d => d.properties.county_name)
        .attr("data-fips", d => d.properties.county_fips)
        .attr("fill", d => colorScale(d.properties.severity_index))
        .attr("d", path);

      featureGroups.each(function(d) {
        const [x, y] = path.centroid(d);
        const g = d3.select(this);
        g.append("text")
          .attr("class", "county-label")
          .attr("x", x)
          .attr("y", y - 4)
          .text(d.properties.county_name.replace(" County", ""));
        g.append("text")
          .attr("class", "county-value")
          .attr("x", x)
          .attr("y", y + 11)
          .text(d.properties.severity_index);
      });
    }

    function renderBars(data) {
      const svg = d3.select("#bars");
      const margin = { top: 12, right: 24, bottom: 40, left: 150 };
      const innerWidth = widthBars - margin.left - margin.right;
      const innerHeight = heightBars - margin.top - margin.bottom;

      const x = d3.scaleLinear()
        .domain([0, 100])
        .range([0, innerWidth]);

      const y = d3.scaleBand()
        .domain(data.map(d => d.county_name))
        .range([0, innerHeight])
        .padding(0.18);

      const root = svg.append("g").attr("transform", "translate(" + margin.left + "," + margin.top + ")");

      root.append("g")
        .attr("class", "grid")
        .call(d3.axisBottom(x).tickSize(innerHeight).tickFormat(""))
        .attr("transform", "translate(0,0)");

      root.append("g")
        .attr("class", "axis")
        .call(d3.axisLeft(y));

      root.append("g")
        .attr("class", "axis")
        .attr("transform", "translate(0," + innerHeight + ")")
        .call(d3.axisBottom(x).ticks(5));

      root.append("text")
        .attr("class", "axis-label")
        .attr("x", innerWidth / 2)
        .attr("y", innerHeight + 34)
        .attr("text-anchor", "middle")
        .text("Severity Index");

      const groups = root.selectAll(".bar-group")
        .data(data)
        .enter()
        .append("g")
        .attr("class", "bar-group")
        .attr("data-county", d => d.county_name)
        .attr("data-fips", d => d.county_fips)
        .attr("data-severity", d => d.severity_index)
        .attr("transform", d => "translate(0," + y(d.county_name) + ")")
        .on("mouseenter", (event, d) => setHovered(d.county_fips, event))
        .on("mousemove", (event, d) => showTooltip(d, event))
        .on("mouseleave", () => clearHovered())
        .on("click", (event, d) => setSelected(d.county_fips, event));

      groups.append("rect")
        .attr("class", "rank-bar")
        .attr("x", 0)
        .attr("y", 0)
        .attr("width", d => x(d.severity_index))
        .attr("height", y.bandwidth())
        .attr("rx", 8)
        .attr("fill", d => colorScale(d.severity_index));

      groups.append("text")
        .attr("x", d => x(d.severity_index) + 10)
        .attr("y", y.bandwidth() / 2 + 4)
        .attr("fill", "#22313b")
        .style("font-weight", "700")
        .style("font-size", "12px")
        .text(d => d.severity_index);
    }

    function setHovered(countyId, event) {
      state.hoveredId = countyId;
      refreshActiveState();
      const record = state.dataById.get(countyId);
      showTooltip(record, event);
    }

    function clearHovered() {
      state.hoveredId = null;
      hideTooltip();
      refreshActiveState();
    }

    function setSelected(countyId, event) {
      state.selectedId = countyId;
      refreshActiveState();
      const record = state.dataById.get(countyId);
      showTooltip(record, event);
    }

    function refreshActiveState() {
      const activeId = state.hoveredId || state.selectedId;
      const activeRecord = state.dataById.get(activeId);

      d3.selectAll(".county-feature")
        .classed("hovered", d => d.properties ? d.properties.county_fips === state.hoveredId : false)
        .classed("selected", d => d.properties ? d.properties.county_fips === state.selectedId : false);

      d3.selectAll(".county-shape")
        .classed("hovered", function() {
          return this.getAttribute("data-fips") === state.hoveredId;
        })
        .classed("selected", function() {
          return this.getAttribute("data-fips") === state.selectedId;
        });

      d3.selectAll(".bar-group")
        .classed("hovered", d => d.county_fips === state.hoveredId)
        .classed("selected", d => d.county_fips === state.selectedId);

      if (activeRecord) {
        updateDetails(activeRecord);
      }
    }

    function updateDetails(record) {
      d3.select("#detail-title").text(record.county_name);
      d3.select("#detail-severity").text(record.severity_index + " / 100");
      d3.select("#detail-customers").text(formatInt(record.customers_out) + " customers out");
      d3.select("#detail-percent").text(formatPercent(record.percent_affected) + " affected");
      d3.select("#detail-eta").text(record.restoration_eta_hours + " hours");
      d3.select("#detail-facility").text(record.critical_facility);
      d3.select("#detail-reported").text(record.reported_at);
      d3.select("#detail-footer").text("Out of " + formatInt(record.total_customers) + " total customers, " + formatPercent(record.percent_affected) + " are currently without service.");
    }

    function showTooltip(record, event) {
      if (!record || !event) {
        return;
      }

      tooltip
        .classed("visible", true)
        .html(
          "<strong>" + record.county_name + "</strong><br>" +
          "Severity index: " + record.severity_index + "<br>" +
          "Customers out: " + formatInt(record.customers_out) + "<br>" +
          "Affected: " + formatPercent(record.percent_affected) + "<br>" +
          "Restoration ETA: " + record.restoration_eta_hours + " hours<br>" +
          "Critical facility: " + record.critical_facility
        )
        .style("left", (event.clientX + 16) + "px")
        .style("top", (event.clientY + 12) + "px");
    }

    function hideTooltip() {
      tooltip.classed("visible", false);
    }
  </script>
</body>
</html>
HTML_EOF
