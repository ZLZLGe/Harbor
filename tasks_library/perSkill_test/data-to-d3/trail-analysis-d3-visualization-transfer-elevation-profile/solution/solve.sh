#!/bin/bash
set -euo pipefail

mkdir -p /root/output/assets /root/output/data

cp /root/data/trail-samples.csv /root/output/data/trail-samples.csv
cp /root/data/trail-waypoints.json /root/output/data/trail-waypoints.json

npm install d3@7.9.0 --prefix /tmp/d3-elevation-profile --silent
cp /tmp/d3-elevation-profile/node_modules/d3/dist/d3.min.js /root/output/assets/d3.v7.min.js

cat > /root/output/elevation-profile.html <<'HTML_EOF'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Trail Elevation Profile Explorer</title>
  <style>
    :root {
      --bg: #f3efe6;
      --panel: rgba(255, 251, 245, 0.9);
      --ink: #22303a;
      --muted: #687782;
      --line: rgba(34, 48, 58, 0.14);
      --accent: #305f72;
      --shadow: 0 20px 44px rgba(45, 57, 66, 0.12);
      --selected: #19323c;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      font-family: "Avenir Next", "PingFang SC", "Noto Sans SC", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(111, 174, 127, 0.22), transparent 24%),
        radial-gradient(circle at bottom right, rgba(240, 170, 95, 0.18), transparent 26%),
        linear-gradient(180deg, #f6f1e8 0%, #eef2ef 100%);
      min-height: 100vh;
    }

    main {
      max-width: 1360px;
      margin: 0 auto;
      padding: 28px 24px 40px;
    }

    .hero {
      display: flex;
      justify-content: space-between;
      gap: 20px;
      align-items: end;
      margin-bottom: 24px;
      flex-wrap: wrap;
    }

    .hero h1 {
      margin: 0 0 10px;
      font-size: 2.4rem;
      letter-spacing: -0.04em;
    }

    .hero p {
      margin: 0;
      max-width: 760px;
      color: var(--muted);
      line-height: 1.6;
    }

    .stats {
      display: flex;
      gap: 14px;
      flex-wrap: wrap;
    }

    .stat {
      min-width: 138px;
      padding: 14px 16px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.7);
      border: 1px solid rgba(255, 255, 255, 0.7);
      box-shadow: var(--shadow);
      backdrop-filter: blur(12px);
    }

    .stat strong {
      display: block;
      font-size: 1.28rem;
      margin-bottom: 4px;
    }

    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1.7fr) minmax(320px, 0.95fr);
      gap: 22px;
      align-items: start;
    }

    .panel {
      background: var(--panel);
      border: 1px solid rgba(255, 255, 255, 0.75);
      border-radius: 26px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(12px);
    }

    .chart-panel {
      padding: 22px 22px 18px;
    }

    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: start;
      gap: 16px;
      margin-bottom: 14px;
      flex-wrap: wrap;
    }

    .panel-header h2,
    .browser-panel h2 {
      margin: 0 0 6px;
      font-size: 1.18rem;
    }

    .muted {
      color: var(--muted);
      font-size: 0.95rem;
    }

    #slope-legend {
      display: flex;
      gap: 10px 12px;
      flex-wrap: wrap;
      margin-bottom: 14px;
    }

    .legend-item {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.72);
      border: 1px solid rgba(34, 48, 58, 0.08);
      color: var(--muted);
      font-size: 0.88rem;
    }

    .legend-swatch {
      width: 12px;
      height: 12px;
      border-radius: 999px;
    }

    #profile-chart {
      width: 100%;
      overflow: hidden;
    }

    #profile-chart svg {
      display: block;
      width: 100%;
      height: auto;
    }

    .axis text {
      fill: var(--muted);
      font-size: 12px;
    }

    .axis path,
    .axis line {
      stroke: rgba(34, 48, 58, 0.16);
    }

    .grid line {
      stroke: rgba(34, 48, 58, 0.08);
      stroke-dasharray: 4 4;
    }

    .area {
      fill: rgba(85, 133, 122, 0.18);
    }

    .baseline-profile {
      fill: none;
      stroke: rgba(40, 66, 73, 0.25);
      stroke-width: 4;
      stroke-linecap: round;
      stroke-linejoin: round;
    }

    .profile-segment {
      fill: none;
      stroke-width: 5;
      stroke-linecap: round;
      stroke-linejoin: round;
    }

    .sample-hotspot {
      fill: rgba(0, 0, 0, 0);
      cursor: crosshair;
    }

    .crosshair {
      stroke: rgba(25, 50, 60, 0.45);
      stroke-dasharray: 5 5;
      stroke-width: 1.5;
      opacity: 0;
    }

    #hover-focus {
      fill: white;
      stroke: var(--selected);
      stroke-width: 3;
      opacity: 0;
    }

    .waypoint-marker circle {
      fill: #fff;
      stroke: rgba(48, 95, 114, 0.7);
      stroke-width: 2;
      transition: r 0.16s ease, fill 0.16s ease, stroke-width 0.16s ease;
    }

    .waypoint-marker text {
      fill: rgba(34, 48, 58, 0.76);
      font-size: 12px;
      font-weight: 600;
      text-anchor: middle;
    }

    .waypoint-marker.is-selected circle {
      fill: #19323c;
      stroke: #19323c;
      stroke-width: 3;
    }

    .waypoint-marker.is-selected text {
      fill: #19323c;
    }

    #waypoint-guide {
      stroke: rgba(25, 50, 60, 0.2);
      stroke-width: 2;
      opacity: 0;
    }

    .browser-panel {
      padding: 20px 20px 22px;
    }

    #waypoint-list {
      display: grid;
      gap: 10px;
      margin-bottom: 18px;
    }

    .waypoint-button {
      width: 100%;
      border: 1px solid rgba(34, 48, 58, 0.1);
      background: rgba(255, 255, 255, 0.72);
      border-radius: 18px;
      padding: 14px 16px;
      text-align: left;
      cursor: pointer;
      transition: transform 0.14s ease, border-color 0.14s ease, background-color 0.14s ease;
    }

    .waypoint-button:hover {
      transform: translateY(-1px);
      border-color: rgba(25, 50, 60, 0.28);
    }

    .waypoint-button[aria-pressed="true"] {
      background: rgba(48, 95, 114, 0.12);
      border-color: rgba(48, 95, 114, 0.34);
      box-shadow: inset 0 0 0 1px rgba(48, 95, 114, 0.08);
    }

    .waypoint-button strong {
      display: block;
      margin-bottom: 4px;
      font-size: 1rem;
      color: var(--ink);
    }

    .waypoint-button span {
      color: var(--muted);
      font-size: 0.92rem;
    }

    #waypoint-detail {
      border-radius: 22px;
      padding: 18px 18px 20px;
      background: rgba(248, 251, 247, 0.88);
      border: 1px solid rgba(34, 48, 58, 0.08);
    }

    #waypoint-detail h3 {
      margin: 0 0 14px;
      font-size: 1.32rem;
    }

    .detail-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 14px;
    }

    .detail-card {
      padding: 12px;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.8);
      border: 1px solid rgba(34, 48, 58, 0.08);
    }

    .detail-card span {
      display: block;
      color: var(--muted);
      font-size: 0.82rem;
      margin-bottom: 4px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .detail-card strong {
      font-size: 1rem;
    }

    #waypoint-detail p {
      margin: 0;
      color: var(--ink);
      line-height: 1.65;
    }

    .tooltip {
      position: absolute;
      pointer-events: none;
      opacity: 0;
      transform: translate(-50%, calc(-100% - 14px));
      background: rgba(25, 35, 43, 0.94);
      color: #fff;
      border-radius: 14px;
      padding: 10px 12px;
      font-size: 13px;
      line-height: 1.55;
      white-space: nowrap;
      box-shadow: 0 16px 36px rgba(17, 24, 39, 0.2);
      transition: opacity 0.12s ease;
      z-index: 10;
    }

    .tooltip.visible {
      opacity: 1;
    }

    @media (max-width: 980px) {
      .layout {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 640px) {
      main {
        padding: 20px 14px 28px;
      }

      .hero h1 {
        font-size: 1.92rem;
      }

      .detail-grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div>
        <h1>云脊穿越高程剖面</h1>
        <p>沿 14.4 公里的连续采样点查看爬升趋势，按坡度区间追踪难点，并在右侧快速切换关键途经点，查看其位置与现场说明。</p>
      </div>
      <div class="stats" id="stats"></div>
    </section>

    <section class="layout">
      <article class="panel chart-panel">
        <div class="panel-header">
          <div>
            <h2>高程剖面</h2>
            <div class="muted">折线按相邻路段坡度分级着色，悬停采样点查看距离、海拔与坡度。</div>
          </div>
          <div class="muted">路线总长 14.4 km</div>
        </div>
        <div id="slope-legend"></div>
        <div id="profile-chart"></div>
      </article>

      <aside class="panel browser-panel">
        <h2>途经点浏览</h2>
        <div class="muted" style="margin-bottom: 14px;">默认聚焦海拔最高的途经点。点击名称可同步查看剖面位置与说明。</div>
        <div id="waypoint-list"></div>
        <section id="waypoint-detail" aria-live="polite">
          <h3></h3>
          <div class="detail-grid">
            <div class="detail-card"><span>Distance</span><strong id="detail-distance"></strong></div>
            <div class="detail-card"><span>Elevation</span><strong id="detail-elevation"></strong></div>
            <div class="detail-card"><span>Category</span><strong id="detail-category"></strong></div>
            <div class="detail-card"><span>ETA</span><strong id="detail-eta"></strong></div>
          </div>
          <p id="detail-note"></p>
        </section>
      </aside>
    </section>
  </main>

  <div id="tooltip" class="tooltip" role="tooltip"></div>

  <script src="assets/d3.v7.min.js"></script>
  <script>
    const legendBins = [
      { label: '0-3.9% 平缓', color: '#7fbf7f', max: 4 },
      { label: '4-7.9% 持续爬升', color: '#f2b35d', max: 8 },
      { label: '8-11.9% 陡坡', color: '#e76f51', max: 12 },
      { label: '12%+ 冲顶段', color: '#8d3b1f', max: Infinity }
    ];

    const formatDistance = value => `${value.toFixed(1)} km`;
    const formatElevation = value => `${Math.round(value)} m`;
    const formatGrade = value => `${value.toFixed(1)}%`;
    const slopeBin = value => legendBins.find(bin => Math.abs(value) < bin.max);

    Promise.all([
      d3.csv('data/trail-samples.csv', d3.autoType),
      d3.json('data/trail-waypoints.json')
    ]).then(([samples, waypoints]) => {
      samples.sort((a, b) => a.distance_km - b.distance_km);
      waypoints.sort((a, b) => a.distance_km - b.distance_km);

      const ascent = d3.sum(d3.pairs(samples), ([a, b]) => Math.max(0, b.elevation_m - a.elevation_m));
      const stats = [
        { label: '总爬升', value: `${Math.round(ascent)} m` },
        { label: '最高海拔', value: `${d3.max(samples, d => d.elevation_m)} m` },
        { label: '途经点', value: `${waypoints.length} 个` }
      ];

      d3.select('#stats')
        .selectAll('.stat')
        .data(stats)
        .enter()
        .append('div')
        .attr('class', 'stat')
        .html(d => `<strong>${d.value}</strong><span>${d.label}</span>`);

      d3.select('#slope-legend')
        .selectAll('.legend-item')
        .data(legendBins)
        .enter()
        .append('div')
        .attr('class', 'legend-item')
        .html(d => `<span class="legend-swatch" style="background:${d.color}"></span><span>${d.label}</span>`);

      const width = 920;
      const height = 520;
      const margin = { top: 26, right: 26, bottom: 50, left: 68 };
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;

      const svg = d3.select('#profile-chart')
        .append('svg')
        .attr('viewBox', `0 0 ${width} ${height}`)
        .attr('aria-label', 'Trail elevation profile');

      const root = svg.append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

      const x = d3.scaleLinear()
        .domain(d3.extent(samples, d => d.distance_km))
        .range([0, innerWidth]);

      const y = d3.scaleLinear()
        .domain([
          d3.min(samples, d => d.elevation_m) - 70,
          d3.max(samples, d => d.elevation_m) + 60
        ])
        .nice()
        .range([innerHeight, 0]);

      root.append('g')
        .attr('class', 'grid')
        .call(
          d3.axisLeft(y)
            .tickSize(-innerWidth)
            .tickFormat('')
        )
        .call(g => g.select('.domain').remove());

      root.append('path')
        .datum(samples)
        .attr('class', 'area')
        .attr('d', d3.area()
          .x(d => x(d.distance_km))
          .y0(innerHeight)
          .y1(d => y(d.elevation_m))
          .curve(d3.curveMonotoneX));

      root.append('path')
        .datum(samples)
        .attr('class', 'baseline-profile')
        .attr('d', d3.line()
          .x(d => x(d.distance_km))
          .y(d => y(d.elevation_m))
          .curve(d3.curveMonotoneX));

      const segments = d3.pairs(samples).map(([from, to], index) => ({
        from,
        to,
        index,
        bin: slopeBin(to.grade_pct)
      }));

      root.append('g')
        .selectAll('.profile-segment')
        .data(segments)
        .enter()
        .append('path')
        .attr('class', 'profile-segment')
        .attr('data-segment-index', d => d.index)
        .attr('data-bin-label', d => d.bin.label)
        .attr('stroke', d => d.bin.color)
        .attr('d', d => d3.line()
          .x(point => x(point.distance_km))
          .y(point => y(point.elevation_m))
          .curve(d3.curveLinear)([d.from, d.to]));

      root.append('g')
        .attr('class', 'axis')
        .attr('transform', `translate(0,${innerHeight})`)
        .call(d3.axisBottom(x).ticks(8).tickFormat(d => `${d.toFixed(1)} km`));

      root.append('g')
        .attr('class', 'axis')
        .call(d3.axisLeft(y).ticks(6).tickFormat(d => `${Math.round(d)} m`));

      const axisLabels = root.append('g');
      axisLabels.append('text')
        .attr('x', innerWidth / 2)
        .attr('y', innerHeight + 42)
        .attr('fill', '#687782')
        .attr('text-anchor', 'middle')
        .text('距离');

      axisLabels.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('x', -innerHeight / 2)
        .attr('y', -48)
        .attr('fill', '#687782')
        .attr('text-anchor', 'middle')
        .text('海拔');

      const crosshairX = root.append('line')
        .attr('id', 'crosshair-x')
        .attr('class', 'crosshair')
        .attr('y1', 0)
        .attr('y2', innerHeight);

      const crosshairY = root.append('line')
        .attr('id', 'crosshair-y')
        .attr('class', 'crosshair')
        .attr('x1', 0)
        .attr('x2', innerWidth);

      const hoverFocus = root.append('circle')
        .attr('id', 'hover-focus')
        .attr('r', 6);

      const tooltip = d3.select('#tooltip');

      const waypointGuide = root.append('line')
        .attr('id', 'waypoint-guide')
        .attr('y1', 0)
        .attr('y2', innerHeight);

      const markerLayer = root.append('g');
      const waypointMarkers = markerLayer.selectAll('.waypoint-marker')
        .data(waypoints)
        .enter()
        .append('g')
        .attr('class', 'waypoint-marker')
        .attr('data-waypoint-id', d => d.id)
        .attr('transform', d => `translate(${x(d.distance_km)},${y(d.elevation_m)})`);

      waypointMarkers.append('circle')
        .attr('r', 6);

      waypointMarkers.append('text')
        .attr('y', -14)
        .text(d => d.name);

      root.append('g')
        .selectAll('.sample-hotspot')
        .data(samples)
        .enter()
        .append('circle')
        .attr('class', 'sample-hotspot')
        .attr('cx', d => x(d.distance_km))
        .attr('cy', d => y(d.elevation_m))
        .attr('r', 15)
        .on('mouseenter', function(event, d) {
          updateHover(event, d);
        })
        .on('mousemove', function(event, d) {
          updateHover(event, d);
        })
        .on('mouseleave', function() {
          tooltip.classed('visible', false);
          crosshairX.style('opacity', 0);
          crosshairY.style('opacity', 0);
          hoverFocus.style('opacity', 0);
        });

      const detail = {
        title: d3.select('#waypoint-detail h3'),
        distance: d3.select('#detail-distance'),
        elevation: d3.select('#detail-elevation'),
        category: d3.select('#detail-category'),
        eta: d3.select('#detail-eta'),
        note: d3.select('#detail-note')
      };

      const buttons = d3.select('#waypoint-list')
        .selectAll('.waypoint-button')
        .data(waypoints)
        .enter()
        .append('button')
        .attr('type', 'button')
        .attr('class', 'waypoint-button')
        .attr('data-waypoint-id', d => d.id)
        .attr('aria-pressed', 'false')
        .html(d => `<strong>${d.name}</strong><span>${formatDistance(d.distance_km)} · ${d.category}</span>`)
        .on('click', (_, d) => selectWaypoint(d.id));

      let selectedWaypointId = null;

      function updateHover(event, d) {
        const cx = x(d.distance_km);
        const cy = y(d.elevation_m);
        crosshairX
          .attr('x1', cx)
          .attr('x2', cx)
          .style('opacity', 1);
        crosshairY
          .attr('y1', cy)
          .attr('y2', cy)
          .style('opacity', 1);
        hoverFocus
          .attr('cx', cx)
          .attr('cy', cy)
          .style('opacity', 1);

        tooltip
          .classed('visible', true)
          .style('left', `${event.pageX}px`)
          .style('top', `${event.pageY}px`)
          .html([
            `距离: ${formatDistance(d.distance_km)}`,
            `海拔: ${formatElevation(d.elevation_m)}`,
            `坡度: ${formatGrade(d.grade_pct)}`
          ].join('<br>'));
      }

      function selectWaypoint(id) {
        selectedWaypointId = id;
        const active = waypoints.find(item => item.id === id);

        buttons
          .attr('aria-pressed', d => d.id === id ? 'true' : 'false');

        waypointMarkers
          .classed('is-selected', d => d.id === id);

        waypointGuide
          .attr('x1', x(active.distance_km))
          .attr('x2', x(active.distance_km))
          .style('opacity', 1);

        detail.title.text(active.name);
        detail.distance.text(formatDistance(active.distance_km));
        detail.elevation.text(formatElevation(active.elevation_m));
        detail.category.text(active.category);
        detail.eta.text(active.eta);
        detail.note.text(active.note);
      }

      const initialWaypoint = waypoints.reduce((best, current) => {
        if (!best) return current;
        if (current.elevation_m > best.elevation_m) return current;
        if (current.elevation_m === best.elevation_m && current.distance_km > best.distance_km) return current;
        return best;
      }, null);

      selectWaypoint(initialWaypoint.id);
    });
  </script>
</body>
</html>
HTML_EOF
