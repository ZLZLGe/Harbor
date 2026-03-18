#!/bin/bash
set -euo pipefail

mkdir -p /root/output/js /root/output/data
cp /root/data/library_circulation.csv /root/output/data/library_circulation.csv

mkdir -p /tmp/library-circulation-d3
cd /tmp/library-circulation-d3
npm install d3@6.7.0 --silent
cp /tmp/library-circulation-d3/node_modules/d3/dist/d3.min.js /root/output/js/d3.v6.min.js

cat > /root/output/circulation-treemap.html <<'HTML_EOF'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Library Circulation Transfer Zoomable Treemap</title>
  <style>
    :root {
      --ink: #18212a;
      --muted: #5f6f7c;
      --line: rgba(24, 33, 42, 0.14);
      --panel: rgba(255, 255, 255, 0.92);
      --shadow: 0 20px 50px rgba(24, 33, 42, 0.14);
      --accent: #8e5a3c;
      --bg-top: #f4efe6;
      --bg-bottom: #e7eef3;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      font-family: "Trebuchet MS", "Gill Sans", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(142, 90, 60, 0.16), transparent 28%),
        radial-gradient(circle at top right, rgba(77, 124, 150, 0.14), transparent 26%),
        linear-gradient(180deg, var(--bg-top), var(--bg-bottom));
    }

    .page {
      max-width: 1440px;
      margin: 0 auto;
      padding: 28px 22px 34px;
    }

    .eyebrow {
      margin: 0 0 10px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      font-size: 0.8rem;
      color: var(--accent);
    }

    h1 {
      margin: 0;
      font-family: "Palatino Linotype", "Book Antiqua", serif;
      font-size: clamp(2.2rem, 3vw, 3.3rem);
      line-height: 1.05;
    }

    .subtitle {
      max-width: 920px;
      margin: 12px 0 0;
      color: var(--muted);
      line-height: 1.55;
      font-size: 1rem;
    }

    .stats {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
      margin: 26px 0 20px;
    }

    .stat-card,
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(4px);
    }

    .stat-card {
      padding: 18px 20px;
    }

    .stat-card span {
      display: block;
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      margin-bottom: 8px;
    }

    .stat-card strong {
      display: block;
      font-size: 1.8rem;
      font-family: "Palatino Linotype", "Book Antiqua", serif;
    }

    .stat-card p {
      margin: 10px 0 0;
      color: var(--muted);
      line-height: 1.4;
      font-size: 0.94rem;
    }

    .panel {
      padding: 18px 18px 20px;
    }

    .panel-header {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      margin-bottom: 12px;
    }

    .panel-header h2 {
      margin: 0;
      font-size: 1.2rem;
    }

    .panel-header p {
      margin: 0;
      max-width: 420px;
      color: var(--muted);
      line-height: 1.45;
      font-size: 0.95rem;
    }

    .breadcrumb {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 14px;
      min-height: 38px;
    }

    .crumb {
      border: 1px solid rgba(24, 33, 42, 0.12);
      background: rgba(250, 248, 245, 0.94);
      border-radius: 999px;
      padding: 8px 12px;
      font: inherit;
      color: var(--ink);
      cursor: pointer;
      transition: transform 0.16s ease, background 0.16s ease;
    }

    .crumb:hover,
    .crumb:focus-visible {
      background: rgba(239, 232, 223, 0.98);
      transform: translateY(-1px);
      outline: none;
    }

    .crumb.current {
      background: rgba(24, 33, 42, 0.9);
      color: #f7f4ef;
      cursor: default;
    }

    .crumb-separator {
      color: var(--muted);
      font-size: 0.86rem;
    }

    .chart-frame {
      position: relative;
      overflow: hidden;
      border-radius: 18px;
      border: 1px solid rgba(24, 33, 42, 0.1);
      background:
        linear-gradient(180deg, rgba(252, 251, 249, 0.98), rgba(244, 247, 249, 0.98));
      min-height: 720px;
    }

    svg {
      width: 100%;
      height: auto;
      display: block;
    }

    .tile rect {
      stroke: rgba(255, 255, 255, 0.94);
      stroke-width: 3px;
      cursor: pointer;
      transition: filter 0.18s ease, transform 0.18s ease, stroke-width 0.18s ease;
    }

    .tile:hover rect {
      filter: brightness(1.03);
      stroke-width: 4px;
    }

    .tile.active rect {
      filter: drop-shadow(0 0 12px rgba(24, 33, 42, 0.2));
    }

    .tile-label {
      pointer-events: none;
      fill: rgba(255, 255, 255, 0.96);
      text-shadow: 0 1px 2px rgba(24, 33, 42, 0.38);
    }

    .tile-label .name {
      font-size: 20px;
      font-weight: 700;
    }

    .tile-label .value {
      font-size: 14px;
      font-weight: 600;
    }

    .tile-label .detail {
      font-size: 12px;
      opacity: 0.92;
    }

    .tile-label.compact .name {
      font-size: 15px;
    }

    .tile-label.compact .value {
      font-size: 12px;
    }

    .tile-label.compact .detail {
      font-size: 11px;
    }

    .tooltip {
      position: absolute;
      min-width: 240px;
      max-width: 320px;
      padding: 12px 14px;
      background: rgba(20, 28, 36, 0.94);
      color: #f7f5f1;
      border-radius: 14px;
      box-shadow: 0 18px 34px rgba(12, 18, 24, 0.28);
      pointer-events: none;
      opacity: 0;
      transform: translateY(6px);
      transition: opacity 0.14s ease, transform 0.14s ease;
      z-index: 20;
    }

    .tooltip.visible {
      opacity: 1;
      transform: translateY(0);
    }

    .tooltip strong {
      display: block;
      font-size: 1rem;
      margin-bottom: 6px;
    }

    .tooltip p {
      margin: 4px 0;
      line-height: 1.35;
      font-size: 0.92rem;
    }

    .tooltip .kicker {
      color: rgba(247, 245, 241, 0.72);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 0.72rem;
      margin-bottom: 8px;
    }

    @media (max-width: 980px) {
      .stats {
        grid-template-columns: 1fr;
      }

      .panel-header {
        flex-direction: column;
      }

      .chart-frame {
        min-height: 560px;
      }
    }

    @media (max-width: 640px) {
      .page {
        padding: 22px 14px 28px;
      }

      .chart-frame {
        min-height: 480px;
      }
    }
  </style>
</head>
<body>
  <div class="page">
    <p class="eyebrow">Citywide Lending Snapshot</p>
    <h1>Library Circulation Explorer</h1>
    <p class="subtitle">
      Drill from the systemwide branch view into genre-level circulation patterns, with breadcrumb context and
      circulation summaries for every branch collection.
    </p>

    <section class="stats" aria-label="System summary">
      <div class="stat-card">
        <span>Total annual circulation</span>
        <strong id="system-total">0</strong>
        <p id="system-note">Loading branch totals...</p>
      </div>
      <div class="stat-card">
        <span>Busiest branch</span>
        <strong id="top-branch">0</strong>
        <p id="top-branch-note">Loading highest branch...</p>
      </div>
      <div class="stat-card">
        <span>Largest genre lane</span>
        <strong id="top-genre">0</strong>
        <p id="top-genre-note">Loading leading genre...</p>
      </div>
    </section>

    <section class="panel">
      <div class="panel-header">
        <div>
          <h2>Zoomable Branch Treemap</h2>
        </div>
        <p>
          Each tile is sized by annual checkouts. Click a branch to expand it, then use the breadcrumb trail to return
          to the full system view.
        </p>
      </div>

      <div id="breadcrumb" class="breadcrumb" aria-label="Breadcrumb trail"></div>

      <div class="chart-frame">
        <svg id="treemap" viewBox="0 0 1280 760" role="img" aria-label="Library circulation treemap"></svg>
        <div id="tooltip" class="tooltip" aria-live="polite"></div>
      </div>
    </section>
  </div>

  <script src="js/d3.v6.min.js"></script>
  <script>
    const width = 1280;
    const height = 760;
    const padding = 14;
    const svg = d3.select("#treemap");
    const tooltip = d3.select("#tooltip");
    const formatter = d3.format(",");
    const waitFormatter = d3.format(".1f");
    const colorByBranch = new Map([
      ["Central Library", "#2f6c63"],
      ["Harbor Point Branch", "#5078a7"],
      ["Maple Grove Branch", "#7f6e3d"],
      ["Eastside Learning Hub", "#97544f"],
      ["West End Branch", "#5c4d7f"]
    ]);

    function branchTone(branch, depth) {
      const base = d3.color(colorByBranch.get(branch) || "#5f7f8a");
      if (!base) return "#5f7f8a";
      if (depth <= 1) return base.formatHex();
      const mix = d3.interpolateRgb(base.formatHex(), "#f4efe6")(0.28);
      return d3.color(mix).formatHex();
    }

    function summarizeBranch(rows, branchName, neighborhood) {
      const annual = d3.sum(rows, d => d.annual_checkouts);
      const titles = d3.sum(rows, d => d.unique_titles);
      const renewals = d3.sum(rows, d => d.renewals);
      const avgWait = d3.sum(rows, d => d.avg_wait_days * d.annual_checkouts) / annual;
      const dominantRow = rows.slice().sort((a, b) => d3.descending(a.annual_checkouts, b.annual_checkouts))[0];

      return {
        name: branchName,
        branch: branchName,
        neighborhood,
        annual_checkouts: annual,
        unique_titles: titles,
        renewals,
        avg_wait_days: avgWait,
        dominant_genre: dominantRow.genre,
        audience: "Mixed Collections"
      };
    }

    function buildHierarchy(rows) {
      const grouped = d3.groups(rows, d => d.branch);
      const branchChildren = grouped.map(([branch, branchRows]) => {
        const neighborhood = branchRows[0].neighborhood;
        const summary = summarizeBranch(branchRows, branch, neighborhood);
        return {
          ...summary,
          children: branchRows
            .slice()
            .sort((a, b) => d3.descending(a.annual_checkouts, b.annual_checkouts))
            .map(row => ({
              name: row.genre,
              branch: row.branch,
              neighborhood: row.neighborhood,
              audience: row.audience,
              annual_checkouts: row.annual_checkouts,
              unique_titles: row.unique_titles,
              renewals: row.renewals,
              avg_wait_days: row.avg_wait_days,
              dominant_genre: row.genre
            }))
        };
      }).sort((a, b) => d3.descending(a.annual_checkouts, b.annual_checkouts));

      return {
        name: "All Branches",
        branch: "All Branches",
        annual_checkouts: d3.sum(branchChildren, d => d.annual_checkouts),
        unique_titles: d3.sum(branchChildren, d => d.unique_titles),
        renewals: d3.sum(branchChildren, d => d.renewals),
        avg_wait_days: d3.sum(branchChildren, d => d.avg_wait_days * d.annual_checkouts) / d3.sum(branchChildren, d => d.annual_checkouts),
        dominant_genre: branchChildren[0].dominant_genre,
        children: branchChildren
      };
    }

    function updateSummaryCards(rows) {
      const totalAnnual = d3.sum(rows, d => d.annual_checkouts);
      const branchTotals = Array.from(
        d3.rollup(rows, values => d3.sum(values, d => d.annual_checkouts), d => d.branch),
        ([branch, total]) => ({ branch, total })
      ).sort((a, b) => d3.descending(a.total, b.total));

      const topGenre = rows.slice().sort((a, b) => d3.descending(a.annual_checkouts, b.annual_checkouts))[0];

      d3.select("#system-total").text(formatter(totalAnnual));
      d3.select("#system-note").text(branchTotals.length + " branch collections in the system.");
      d3.select("#top-branch").text(branchTotals[0].branch);
      d3.select("#top-branch-note").text(formatter(branchTotals[0].total) + " annual checkouts.");
      d3.select("#top-genre").text(topGenre.branch + " / " + topGenre.genre);
      d3.select("#top-genre-note").text(formatter(topGenre.annual_checkouts) + " annual checkouts in the leading genre tile.");
    }

    function tooltipHtml(node) {
      const data = node.data;
      if (node.depth === 1) {
        return `
          <div class="kicker">Branch Summary</div>
          <strong>${data.branch}</strong>
          <p>Neighborhood: ${data.neighborhood}</p>
          <p>Annual checkouts: ${formatter(data.annual_checkouts)}</p>
          <p>Unique titles: ${formatter(data.unique_titles)}</p>
          <p>Renewals: ${formatter(data.renewals)}</p>
          <p>Average wait time: ${waitFormatter(data.avg_wait_days)} days</p>
          <p>Dominant genre: ${data.dominant_genre}</p>
        `;
      }

      return `
        <div class="kicker">Genre Summary</div>
        <strong>${data.branch} / ${data.name}</strong>
        <p>Audience: ${data.audience}</p>
        <p>Annual checkouts: ${formatter(data.annual_checkouts)}</p>
        <p>Unique titles: ${formatter(data.unique_titles)}</p>
        <p>Renewals: ${formatter(data.renewals)}</p>
        <p>Average wait time: ${waitFormatter(data.avg_wait_days)} days</p>
      `;
    }

    function labelLines(node) {
      if (node.depth === 1) {
        return [node.data.name, formatter(node.data.annual_checkouts), node.data.neighborhood];
      }
      return [node.data.name, formatter(node.data.annual_checkouts), node.data.audience];
    }

    d3.csv("data/library_circulation.csv", d3.autoType).then(rows => {
      updateSummaryCards(rows);

      const rootData = buildHierarchy(rows);
      const root = d3.hierarchy(rootData)
        .sum(d => d.annual_checkouts || 0)
        .sort((a, b) => d3.descending(a.value, b.value));

      d3.treemap()
        .size([width, height])
        .paddingOuter(10)
        .paddingInner(6)
        .round(true)(root);

      let currentNode = root;
      const layer = svg.append("g");

      function updateBreadcrumb(node) {
        const trail = node.ancestors().reverse();
        const container = d3.select("#breadcrumb");
        container.selectAll("*").remove();

        trail.forEach((ancestor, index) => {
          container.append("button")
            .attr("type", "button")
            .attr("class", ancestor === node ? "crumb current" : "crumb")
            .attr("aria-current", ancestor === node ? "page" : null)
            .text(ancestor.data.name)
            .on("click", () => {
              if (ancestor !== currentNode) {
                render(ancestor);
              }
            });

          if (index < trail.length - 1) {
            container.append("span")
              .attr("class", "crumb-separator")
              .text(">");
          }
        });
      }

      function moveTooltip(event) {
        const frame = document.querySelector(".chart-frame").getBoundingClientRect();
        const x = event.clientX - frame.left + 16;
        const y = event.clientY - frame.top + 16;
        tooltip.style("left", x + "px").style("top", y + "px");
      }

      function render(node) {
        currentNode = node;
        updateBreadcrumb(node);

        const children = node.children || [];
        const x = d3.scaleLinear().domain([node.x0, node.x1]).range([padding, width - padding]);
        const y = d3.scaleLinear().domain([node.y0, node.y1]).range([padding, height - padding]);

        const tiles = layer.selectAll("g.tile")
          .data(children, d => d.data.branch + "-" + d.data.name);

        tiles.exit()
          .transition()
          .duration(220)
          .style("opacity", 0)
          .remove();

        const entered = tiles.enter()
          .append("g")
          .attr("class", "tile active")
          .style("opacity", 0);

        entered.append("rect");
        entered.append("text").attr("class", "tile-label");

        const merged = entered.merge(tiles);

        merged
          .on("mouseenter", function(event, d) {
            tooltip.html(tooltipHtml(d)).classed("visible", true);
            moveTooltip(event);
          })
          .on("mousemove", moveTooltip)
          .on("mouseleave", function() {
            tooltip.classed("visible", false);
          })
          .on("click", function(event, d) {
            if (d.children) {
              render(d);
            }
          });

        merged.transition()
          .duration(380)
          .style("opacity", 1)
          .attr("transform", d => `translate(${x(d.x0)},${y(d.y0)})`);

        merged.select("rect").transition()
          .duration(380)
          .attr("width", d => Math.max(0, x(d.x1) - x(d.x0)))
          .attr("height", d => Math.max(0, y(d.y1) - y(d.y0)))
          .attr("fill", d => branchTone(d.data.branch, d.depth));

        merged.select("text")
          .attr("class", d => {
            const rectWidth = x(d.x1) - x(d.x0);
            const rectHeight = y(d.y1) - y(d.y0);
            return rectWidth < 210 || rectHeight < 135 ? "tile-label compact" : "tile-label";
          })
          .each(function(d) {
            const text = d3.select(this);
            const rectWidth = x(d.x1) - x(d.x0);
            const rectHeight = y(d.y1) - y(d.y0);
            const lines = labelLines(d);
            const lineHeight = rectHeight < 130 ? 18 : 24;
            text.selectAll("tspan").remove();
            lines.forEach((line, index) => {
              text.append("tspan")
                .attr("class", index === 0 ? "name" : (index === 1 ? "value" : "detail"))
                .attr("x", 16)
                .attr("y", 28 + index * lineHeight)
                .text(line);
            });

            if (rectWidth < 130 || rectHeight < 86) {
              text.selectAll(".detail").remove();
            }

            if (rectWidth < 95 || rectHeight < 58) {
              text.selectAll(".value").remove();
            }
          });
      }

      render(root);
    });
  </script>
</body>
</html>
HTML_EOF
