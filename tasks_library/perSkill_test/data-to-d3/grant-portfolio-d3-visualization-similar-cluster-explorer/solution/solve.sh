#!/bin/bash
set -euo pipefail

mkdir -p /root/output/js /root/output/data
cp /root/data/grants.csv /root/output/data/grants.csv

mkdir -p /tmp/grant-d3-lib
cd /tmp/grant-d3-lib
npm install d3@6.7.0 --silent
cp /tmp/grant-d3-lib/node_modules/d3/dist/d3.min.js /root/output/js/d3.v6.min.js

GRANTS_JSON=$(python3 - <<'PY'
import csv
import json

with open('/root/data/grants.csv', newline='') as handle:
    rows = list(csv.DictReader(handle))

for row in rows:
    row["award_amount"] = int(row["award_amount"])
    row["start_year"] = int(row["start_year"])

print(json.dumps(rows))
PY
)

cat > /root/output/grant-clusters.html <<HTML
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>University Grants Similar Cluster Explorer</title>
  <style>
    :root {
      --ink: #182430;
      --muted: #5d6b78;
      --panel: #ffffff;
      --page-top: #edf4ff;
      --page-bottom: #f7f3ea;
      --line: #d5dde5;
      --accent: #0f5b78;
      --shadow: 0 18px 40px rgba(24, 36, 48, 0.12);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      font-family: "Trebuchet MS", "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(86, 141, 255, 0.18), transparent 30%),
        linear-gradient(180deg, var(--page-top), var(--page-bottom));
      min-height: 100vh;
    }

    .page {
      max-width: 1480px;
      margin: 0 auto;
      padding: 28px 22px 40px;
    }

    h1 {
      margin: 0 0 10px;
      font-size: 2rem;
      letter-spacing: 0.02em;
    }

    .subtitle {
      margin: 0 0 24px;
      color: var(--muted);
      max-width: 900px;
      line-height: 1.5;
    }

    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(360px, 0.95fr);
      gap: 22px;
      align-items: start;
    }

    .panel {
      background: rgba(255, 255, 255, 0.9);
      border: 1px solid rgba(213, 221, 229, 0.9);
      border-radius: 20px;
      padding: 20px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(4px);
    }

    .panel-header {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: baseline;
      margin-bottom: 14px;
    }

    .panel-header h2 {
      margin: 0;
      font-size: 1.15rem;
    }

    .panel-header p {
      margin: 0;
      color: var(--muted);
      font-size: 0.95rem;
    }

    .legend {
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
      background: rgba(245, 248, 251, 0.95);
      border: 1px solid var(--line);
      font-size: 0.92rem;
    }

    .legend-swatch {
      width: 14px;
      height: 14px;
      border-radius: 50%;
      border: 1px solid rgba(24, 36, 48, 0.25);
      flex: 0 0 auto;
    }

    svg {
      width: 100%;
      height: auto;
      display: block;
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(243, 247, 250, 0.96));
      border-radius: 16px;
      border: 1px solid rgba(213, 221, 229, 0.85);
    }

    .cluster-note {
      font-size: 0.82rem;
      fill: #6b7785;
      text-anchor: middle;
      letter-spacing: 0.04em;
    }

    .node {
      cursor: pointer;
    }

    .node circle {
      stroke: rgba(24, 36, 48, 0.7);
      stroke-width: 1.4px;
      transition: stroke-width 0.18s ease, filter 0.18s ease, opacity 0.18s ease;
    }

    .node:hover circle,
    .node.selected circle {
      stroke: #0b1a22;
      stroke-width: 3.6px;
      filter: drop-shadow(0 0 10px rgba(15, 91, 120, 0.35));
    }

    .bubble-label {
      fill: #11212b;
      font-size: 10px;
      font-weight: 700;
      text-anchor: middle;
      pointer-events: none;
      user-select: none;
    }

    .table-wrap {
      overflow: auto;
      max-height: 760px;
      border: 1px solid rgba(213, 221, 229, 0.85);
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.96);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 760px;
    }

    thead th {
      position: sticky;
      top: 0;
      background: #f0f6fa;
      border-bottom: 1px solid var(--line);
      padding: 12px 14px;
      text-align: left;
      font-size: 0.88rem;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      cursor: pointer;
      z-index: 1;
    }

    tbody td {
      padding: 12px 14px;
      border-bottom: 1px solid #e6edf2;
      vertical-align: top;
      font-size: 0.94rem;
    }

    tbody tr {
      cursor: pointer;
      transition: background-color 0.16s ease, color 0.16s ease;
    }

    tbody tr:hover {
      background: #eff7ff;
    }

    tbody tr.selected {
      background: #d9eefc;
      color: #072a3a;
      font-weight: 700;
    }

    .project-cell {
      min-width: 230px;
    }

    .sort-indicator {
      margin-left: 6px;
      font-size: 0.82rem;
      color: var(--accent);
    }

    .tooltip {
      position: fixed;
      z-index: 20;
      max-width: 300px;
      padding: 12px 14px;
      border-radius: 12px;
      background: rgba(11, 26, 34, 0.94);
      color: #f7fbff;
      font-size: 0.9rem;
      line-height: 1.45;
      box-shadow: 0 12px 30px rgba(11, 26, 34, 0.28);
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
      margin-bottom: 4px;
      font-size: 0.95rem;
    }

    .summary {
      display: flex;
      gap: 14px;
      flex-wrap: wrap;
      margin-bottom: 16px;
    }

    .metric {
      padding: 12px 14px;
      border-radius: 14px;
      background: rgba(244, 248, 251, 0.96);
      border: 1px solid var(--line);
      min-width: 160px;
    }

    .metric-label {
      display: block;
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--muted);
      margin-bottom: 6px;
    }

    .metric-value {
      font-size: 1.12rem;
      font-weight: 700;
    }

    @media (max-width: 1120px) {
      .layout {
        grid-template-columns: 1fr;
      }

      .table-wrap {
        max-height: none;
      }
    }
  </style>
</head>
<body>
  <div class="page">
    <h1>University Grants Similar Cluster Explorer</h1>
    <p class="subtitle">Compare 18 research awards by sponsor type, scan funding concentration, and inspect linked grant details in the coordinated table.</p>

    <div class="summary" id="summary"></div>

    <div class="layout">
      <section class="panel">
        <div class="panel-header">
          <h2>Force-Clustered Grant Bubbles</h2>
          <p>Bubble size shows award amount. Color and layout follow sponsor type.</p>
        </div>
        <div class="legend" id="legend"></div>
        <svg id="cluster-chart" viewBox="0 0 820 620" aria-label="University grant bubble chart"></svg>
      </section>

      <section class="panel">
        <div class="panel-header">
          <h2>Sortable Grants Table</h2>
          <p>Click any column header to reorder the portfolio.</p>
        </div>
        <div class="table-wrap">
          <table id="grants-table">
            <thead></thead>
            <tbody></tbody>
          </table>
        </div>
      </section>
    </div>
  </div>

  <div id="tooltip" class="tooltip" role="status" aria-live="polite"></div>

  <script src="js/d3.v6.min.js"></script>
  <script>
    const grants = ${GRANTS_JSON};

    const sponsorPalette = {
      Corporate: "#f28e2b",
      Federal: "#4e79a7",
      Foundation: "#59a14f",
      International: "#af7aa1",
      State: "#e15759"
    };

    const chartWidth = 820;
    const chartHeight = 620;
    const sponsorTypes = Array.from(new Set(grants.map((grant) => grant.sponsor_type))).sort();
    const sortLabels = {
      grant_id: "Grant ID",
      university: "University",
      project_title: "Project",
      sponsor_type: "Sponsor Type",
      award_amount: "Award Amount",
      start_year: "Start Year"
    };

    let selectedGrantId = null;
    let sortState = { key: "award_amount", direction: "desc" };

    const svg = d3.select("#cluster-chart");
    const tooltip = d3.select("#tooltip");
    const legend = d3.select("#legend");
    const summary = d3.select("#summary");
    const tbody = d3.select("#grants-table tbody");
    const thead = d3.select("#grants-table thead");

    function formatAward(value) {
      if (value >= 1_000_000_000) {
        return "$" + (value / 1_000_000_000).toFixed(2) + "B";
      }
      if (value >= 1_000_000) {
        return "$" + (value / 1_000_000).toFixed(2) + "M";
      }
      if (value >= 1_000) {
        return "$" + (value / 1_000).toFixed(1) + "K";
      }
      return "$" + value;
    }

    function compareValues(a, b, key) {
      if (key === "award_amount" || key === "start_year") {
        return a[key] - b[key];
      }
      return String(a[key]).localeCompare(String(b[key]));
    }

    function getSortedGrants() {
      return [...grants].sort((a, b) => {
        const comparison = compareValues(a, b, sortState.key);
        return sortState.direction === "asc" ? comparison : -comparison;
      });
    }

    function renderSummary() {
      const totalFunding = grants.reduce((sum, grant) => sum + grant.award_amount, 0);
      const metrics = [
        { label: "Total Awards", value: grants.length },
        { label: "Total Funding", value: formatAward(totalFunding) },
        { label: "Sponsor Types", value: sponsorTypes.length }
      ];

      summary.selectAll(".metric")
        .data(metrics)
        .join("div")
        .attr("class", "metric")
        .html((metric) => (
          '<span class="metric-label">' + metric.label + '</span>' +
          '<span class="metric-value">' + metric.value + '</span>'
        ));
    }

    function renderLegend() {
      legend.selectAll(".legend-item")
        .data(sponsorTypes)
        .join("div")
        .attr("class", "legend-item")
        .html((type) => (
          '<span class="legend-swatch" style="background:' + sponsorPalette[type] + ';"></span>' +
          '<span>' + type + '</span>'
        ));
    }

    function buildNodes() {
      const radiusScale = d3.scaleSqrt()
        .domain(d3.extent(grants, (grant) => grant.award_amount))
        .range([22, 52]);

      const clusterCenters = {
        Corporate: { x: 180, y: 210 },
        Federal: { x: 410, y: 180 },
        Foundation: { x: 660, y: 220 },
        International: { x: 280, y: 430 },
        State: { x: 560, y: 430 }
      };

      const nodes = grants.map((grant, index) => ({
        ...grant,
        radius: radiusScale(grant.award_amount),
        x: clusterCenters[grant.sponsor_type].x + ((index % 4) - 1.5) * 12,
        y: clusterCenters[grant.sponsor_type].y + (Math.floor(index / 4) - 2) * 12
      }));

      const simulation = d3.forceSimulation(nodes)
        .force("x", d3.forceX((node) => clusterCenters[node.sponsor_type].x).strength(0.18))
        .force("y", d3.forceY((node) => clusterCenters[node.sponsor_type].y).strength(0.18))
        .force("charge", d3.forceManyBody().strength(3))
        .force("collide", d3.forceCollide((node) => node.radius + 2))
        .stop();

      for (let i = 0; i < 280; i += 1) {
        simulation.tick();
      }

      return { nodes, clusterCenters };
    }

    function showTooltip(event, grant) {
      tooltip
        .classed("visible", true)
        .html(
          "<strong>" + grant.grant_id + "</strong>" +
          "University: " + grant.university + "<br>" +
          "Project: " + grant.project_title + "<br>" +
          "Sponsor: " + grant.sponsor + "<br>" +
          "Sponsor Type: " + grant.sponsor_type + "<br>" +
          "Award Amount: " + formatAward(grant.award_amount) + "<br>" +
          "Start Year: " + grant.start_year
        )
        .style("left", (event.clientX + 16) + "px")
        .style("top", (event.clientY + 16) + "px");
    }

    function moveTooltip(event) {
      tooltip
        .style("left", (event.clientX + 16) + "px")
        .style("top", (event.clientY + 16) + "px");
    }

    function hideTooltip() {
      tooltip.classed("visible", false);
    }

    function syncSelection() {
      d3.selectAll(".node").classed("selected", (node) => node.grant_id === selectedGrantId);
      d3.selectAll("#grants-table tbody tr").classed("selected", (grant) => grant.grant_id === selectedGrantId);
    }

    function selectGrant(grantId) {
      selectedGrantId = grantId;
      syncSelection();
    }

    function renderTable() {
      const headers = [
        { key: "grant_id", label: sortLabels.grant_id },
        { key: "university", label: sortLabels.university },
        { key: "project_title", label: sortLabels.project_title },
        { key: "sponsor_type", label: sortLabels.sponsor_type },
        { key: "award_amount", label: sortLabels.award_amount },
        { key: "start_year", label: sortLabels.start_year }
      ];

      thead.selectAll("tr")
        .data([headers])
        .join("tr")
        .selectAll("th")
        .data((row) => row)
        .join("th")
        .text((header) => header.label)
        .append("span")
        .attr("class", "sort-indicator")
        .text((header) => {
          if (header.key !== sortState.key) {
            return "";
          }
          return sortState.direction === "asc" ? "▲" : "▼";
        });

      thead.selectAll("th")
        .on("click", function(event, header) {
          if (sortState.key === header.key) {
            sortState.direction = sortState.direction === "asc" ? "desc" : "asc";
          } else {
            sortState.key = header.key;
            sortState.direction = header.key === "award_amount" || header.key === "start_year" ? "desc" : "asc";
          }
          renderTable();
        });

      const rows = tbody.selectAll("tr")
        .data(getSortedGrants(), (grant) => grant.grant_id)
        .join("tr")
        .on("click", function(event, grant) {
          selectGrant(grant.grant_id);
        });

      const cells = rows.selectAll("td")
        .data((grant) => [
          grant.grant_id,
          grant.university,
          grant.project_title,
          grant.sponsor_type,
          formatAward(grant.award_amount),
          grant.start_year
        ])
        .join("td")
        .text((value) => value);

      rows.select("td:nth-child(3)").attr("class", "project-cell");
      syncSelection();
    }

    function renderChart() {
      const { nodes, clusterCenters } = buildNodes();

      svg.append("rect")
        .attr("x", 0)
        .attr("y", 0)
        .attr("width", chartWidth)
        .attr("height", chartHeight)
        .attr("fill", "transparent");

      svg.selectAll(".cluster-note")
        .data(sponsorTypes)
        .join("text")
        .attr("class", "cluster-note")
        .attr("x", (type) => clusterCenters[type].x)
        .attr("y", (type) => clusterCenters[type].y - 72)
        .text((type) => type);

      const nodeGroups = svg.selectAll(".node")
        .data(nodes)
        .join("g")
        .attr("class", "node")
        .attr("transform", (node) => "translate(" + node.x + "," + node.y + ")")
        .on("mouseenter", function(event, node) {
          showTooltip(event, node);
        })
        .on("mousemove", function(event) {
          moveTooltip(event);
        })
        .on("mouseleave", function() {
          hideTooltip();
        })
        .on("click", function(event, node) {
          selectGrant(node.grant_id);
        });

      nodeGroups.append("circle")
        .attr("r", (node) => node.radius)
        .attr("fill", (node) => sponsorPalette[node.sponsor_type]);
      nodeGroups.append("text")
        .attr("class", "bubble-label")
        .attr("dy", "0.35em")
        .style("font-size", (node) => node.radius < 28 ? "8px" : "10px")
        .text((node) => node.grant_id);
    }

    renderSummary();
    renderLegend();
    renderChart();
    renderTable();
  </script>
</body>
</html>
HTML
