#!/bin/bash
set -euo pipefail

mkdir -p /root/output

node --input-type=module <<'NODE'
import fs from "node:fs";
import * as d3 from "d3";

const inputPath = "/root/data/library_daily_checkouts_2025.csv";
const outputPath = "/root/output/library-checkout-heatmap.svg";

const parseDate = d3.utcParse("%Y-%m-%d");
const monthKeyFormat = d3.utcFormat("%Y-%m");
const monthLabelFormat = d3.utcFormat("%B %Y");

const rawRows = d3.csvParse(fs.readFileSync(inputPath, "utf8"));
const rows = rawRows.map((row) => {
  const date = parseDate(row.date);
  return {
    date,
    dateString: row.date,
    checkoutCount: Number.parseInt(row.checkout_count, 10),
    holidayName: row.holiday_name || "",
    eventLabel: row.event_label || "",
  };
});

const counts = rows.map((row) => row.checkoutCount);
const minCount = d3.min(counts);
const maxCount = d3.max(counts);
const colorScale = d3.scaleSequential(d3.interpolateYlOrRd).domain([minCount, maxCount]);

const months = d3.utcMonths(new Date(Date.UTC(2025, 0, 1)), new Date(Date.UTC(2026, 0, 1)));
const rowsByMonth = d3.group(rows, (row) => monthKeyFormat(row.date));

const panelWidth = 220;
const panelHeight = 190;
const panelGapX = 24;
const panelGapY = 24;
const monthColumns = 3;
const panelLeft = 42;
const panelTop = 92;
const sidebarX = panelLeft + monthColumns * panelWidth + (monthColumns - 1) * panelGapX + 60;
const cellSize = 18;
const cellGap = 4;
const weekdayHeaderY = 26;
const gridOffsetY = 38;
const width = 1120;
const height = 950;
const weekdayLabels = ["M", "T", "W", "T", "F", "S", "S"];

const xmlEscape = (value) =>
  String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

const weekdayIndex = (date) => (date.getUTCDay() + 6) % 7;
const weekIndex = (date) => d3.utcMonday.count(d3.utcMonth(date), date);

const peaks = [...rows]
  .sort((a, b) => d3.descending(a.checkoutCount, b.checkoutCount) || d3.ascending(a.dateString, b.dateString))
  .slice(0, 3);

const legendSteps = d3.range(5).map((index) =>
  minCount + ((maxCount - minCount) * index) / 4
);

const parts = [];
parts.push('<?xml version="1.0" encoding="UTF-8"?>');
parts.push(
  `<svg xmlns="http://www.w3.org/2000/svg" id="library-checkout-report" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`
);
parts.push("<style>");
parts.push(`
  text {
    fill: #23313f;
    font-family: Arial, sans-serif;
  }
  .report-title {
    font-size: 28px;
    font-weight: 700;
  }
  .report-subtitle {
    font-size: 14px;
    fill: #4c6070;
  }
  .month-label {
    font-size: 14px;
    font-weight: 700;
  }
  .weekday-label {
    font-size: 10px;
    fill: #5a6b77;
  }
  .month-frame {
    fill: #fffdf8;
    stroke: #d9d1c3;
    stroke-width: 1;
    rx: 12;
    ry: 12;
  }
  .day-cell {
    stroke: #ffffff;
    stroke-width: 1;
  }
  .day-cell.weekend {
    stroke: #44515c;
    stroke-width: 1.4;
    stroke-dasharray: 2 1;
  }
  .holiday-marker {
    fill: #143642;
    stroke: #ffffff;
    stroke-width: 1;
  }
  .legend-title,
  .section-title {
    font-size: 16px;
    font-weight: 700;
  }
  .legend-label,
  .legend-min,
  .legend-max,
  .annotation-help,
  .summary-note {
    font-size: 12px;
    fill: #51606d;
  }
  .peak-annotation {
    font-size: 13px;
    fill: #23313f;
  }
`);
parts.push("</style>");
parts.push(`<rect x="0" y="0" width="${width}" height="${height}" fill="#f7f3ea"/>`);
parts.push(`<text class="report-title" x="42" y="48">2025 Library Checkout Calendar</text>`);
parts.push(
  `<text class="report-subtitle" x="42" y="72">Daily circulation volume grouped by month with weekend and holiday highlights.</text>`
);

months.forEach((monthDate, index) => {
  const monthKey = monthKeyFormat(monthDate);
  const monthRows = [...(rowsByMonth.get(monthKey) || [])].sort((a, b) => d3.ascending(a.dateString, b.dateString));
  const panelX = panelLeft + (index % monthColumns) * (panelWidth + panelGapX);
  const panelY = panelTop + Math.floor(index / monthColumns) * (panelHeight + panelGapY);

  parts.push(`<g class="month-panel" data-month="${monthKey}" transform="translate(${panelX},${panelY})">`);
  parts.push(`<rect class="month-frame" x="-12" y="-18" width="${panelWidth}" height="${panelHeight}" />`);
  parts.push(`<text class="month-label" x="0" y="0">${xmlEscape(monthLabelFormat(monthDate))}</text>`);

  weekdayLabels.forEach((label, weekday) => {
    const x = weekday * (cellSize + cellGap) + cellSize / 2;
    parts.push(`<text class="weekday-label" x="${x}" y="${weekdayHeaderY}" text-anchor="middle">${label}</text>`);
  });

  monthRows.forEach((row) => {
    const weekday = weekdayIndex(row.date);
    const week = weekIndex(row.date);
    const x = weekday * (cellSize + cellGap);
    const y = gridOffsetY + week * (cellSize + cellGap);
    const isWeekend = weekday >= 5;
    const isHoliday = row.holidayName.length > 0;
    const classNames = ["day-cell"];
    if (isWeekend) {
      classNames.push("weekend");
    }

    const attrs = [
      `class="${classNames.join(" ")}"`,
      `x="${x}"`,
      `y="${y}"`,
      `width="${cellSize}"`,
      `height="${cellSize}"`,
      `rx="3"`,
      `ry="3"`,
      `fill="${colorScale(row.checkoutCount)}"`,
      `data-date="${row.dateString}"`,
      `data-count="${row.checkoutCount}"`,
      `data-month="${monthKey}"`,
      `data-weekday="${weekday}"`,
      `data-week-index="${week}"`,
      `data-weekend="${isWeekend ? "true" : "false"}"`,
      `data-holiday="${isHoliday ? "true" : "false"}"`,
    ];

    if (isHoliday) {
      attrs.push(`data-holiday-name="${xmlEscape(row.holidayName)}"`);
    }

    parts.push(`<rect ${attrs.join(" ")} />`);

    if (isHoliday) {
      const cx = x + cellSize - 4;
      const cy = y + 4;
      parts.push(`<circle class="holiday-marker" data-date="${row.dateString}" cx="${cx}" cy="${cy}" r="3.2" />`);
    }
  });

  parts.push("</g>");
});

parts.push(`<g id="checkout-legend" transform="translate(${sidebarX},118)">`);
parts.push(`<text class="legend-title" x="0" y="0">Checkout legend</text>`);
parts.push(`<text class="annotation-help" x="0" y="22">Lighter to darker means lower to higher daily circulation.</text>`);
legendSteps.forEach((value, index) => {
  const y = 40 + index * 28;
  const rounded = Math.round(value);
  parts.push(
    `<rect class="legend-swatch" x="0" y="${y}" width="26" height="18" rx="3" ry="3" fill="${colorScale(value)}" data-threshold="${rounded}" />`
  );
  parts.push(`<text class="legend-label" x="38" y="${y + 13}">about ${rounded}</text>`);
});
parts.push(`<text class="legend-min" x="0" y="190">Min ${minCount}</text>`);
parts.push(`<text class="legend-max" x="120" y="190">Max ${maxCount}</text>`);
parts.push("</g>");

parts.push(`<g transform="translate(${sidebarX},356)">`);
parts.push(`<text class="section-title" x="0" y="0">Reading pattern notes</text>`);
parts.push(`<text class="summary-note" x="0" y="24">Weekend cells use dashed outlines.</text>`);
parts.push(`<text class="summary-note" x="0" y="44">Holiday dates add a dark circular marker.</text>`);
parts.push("</g>");

parts.push(`<g id="peak-annotations" transform="translate(${sidebarX},456)">`);
parts.push(`<text class="section-title" x="0" y="0">Peak circulation dates</text>`);
peaks.forEach((row, index) => {
  const label =
    `${row.dateString} - ${row.checkoutCount} checkouts` +
    (row.eventLabel ? ` - ${row.eventLabel}` : "");
  parts.push(
    `<text class="peak-annotation" data-date="${row.dateString}" x="0" y="${32 + index * 30}">${xmlEscape(label)}</text>`
  );
});
parts.push("</g>");

parts.push("</svg>");

fs.writeFileSync(outputPath, parts.join("\n"), "utf8");
NODE
