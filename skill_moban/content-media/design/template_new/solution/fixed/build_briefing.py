#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import textwrap
import urllib.request
from pathlib import Path

DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/root/environment/data"))
REGISTRY = os.environ.get("SOURCE_REGISTRY_URL", "http://127.0.0.1:4873")
PREVIEW_ROOT = Path(os.environ.get("STYLE_PREVIEW_ROOT", "/root/.ecc-design/slide-previews"))
PRESET_EXPLORATIONS = [
    (
        "Dark Botanical",
        "#071411",
        "#f5f0e6",
        "Executive calm with editorial contrast and grounded depth.",
    ),
    (
        "Electric Studio",
        "#0d1117",
        "#f5f7fb",
        "Agency-clean split composition with sharper signal framing.",
    ),
    (
        "Notebook Tabs",
        "#f4efe2",
        "#182024",
        "Structured report feel with tabbed navigation and paper texture.",
    ),
]
CHOSEN_PRESET = "Dark Botanical"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def request_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def resolve_sources(source_ids: list[str]) -> list[dict]:
    request_json(f"{REGISTRY}/health")
    resolved = []
    for source_id in source_ids:
        resolved.append(request_json(f"{REGISTRY}/sources/{source_id}"))
    return resolved


def fmt_num(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}"


def slugify(title: str) -> str:
    return (
        title.lower()
        .replace(" ", "-")
        .replace("&", "and")
        .replace("/", "-")
    )


def chart_path(values: list[float], width: int, height: int, left: int, bottom: int, top: int) -> str:
    max_val = max(values)
    min_val = min(values)
    span = max(max_val - min_val, 1)
    usable_width = width - left - 40
    usable_height = height - top - bottom
    points = []
    for idx, value in enumerate(values):
        x = left + idx * usable_width / max(len(values) - 1, 1)
        normalized = (value - min_val) / span
        y = top + usable_height - normalized * usable_height
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)


def build_line_chart(rows: list[dict]) -> str:
    years = [row["year"] for row in rows]
    values = [float(row["renewables_electricity_twh"]) for row in rows]
    path = chart_path(values, 960, 420, 72, 56, 36)
    grid = []
    for idx, year in enumerate(years):
        x = 72 + idx * (960 - 72 - 40) / max(len(years) - 1, 1)
        grid.append(f'<text x="{x:.1f}" y="392" class="axis-label">{year}</text>')
    return f"""
<svg viewBox="0 0 960 420" class="chart" aria-labelledby="growth-title" role="img" data-chart-id="global_growth_line">
  <title id="growth-title">World renewable electricity generation, 2014 to 2023</title>
  <rect x="0" y="0" width="960" height="420" rx="24" fill="#10231d"></rect>
  <g stroke="rgba(240,235,224,0.12)" stroke-width="1">
    <path d="M72 80H920"></path>
    <path d="M72 170H920"></path>
    <path d="M72 260H920"></path>
    <path d="M72 350H920"></path>
  </g>
  <polyline fill="none" stroke="#b9ff63" stroke-width="5" points="{path}"></polyline>
  {"".join(grid)}
  <text x="72" y="42" class="chart-kicker">Renewables electricity generation (TWh)</text>
</svg>
"""


def build_mix_chart(latest: dict) -> str:
    values = [
        ("Solar", float(latest["solar_electricity_twh"]), "#c8ff7a"),
        ("Wind", float(latest["wind_electricity_twh"]), "#6de4c2"),
        ("Hydro", float(latest["hydro_electricity_twh"]), "#66a8ff"),
    ]
    total = sum(value for _, value, _ in values)
    x = 40
    rects = []
    labels = []
    for label, value, color in values:
        width = 820 * value / total
        rects.append(f'<rect x="{x:.1f}" y="120" width="{width:.1f}" height="96" rx="18" fill="{color}"></rect>')
        labels.append(
            f'<text x="{x + 18:.1f}" y="176" class="segment-label">{label} {value:.0f} TWh</text>'
        )
        x += width + 10
    return f"""
<svg viewBox="0 0 900 280" class="chart" aria-labelledby="mix-title" role="img" data-chart-id="mix_shift_stack">
  <title id="mix-title">2023 world renewable electricity by technology</title>
  <rect x="0" y="0" width="900" height="280" rx="24" fill="#10231d"></rect>
  <text x="40" y="60" class="chart-kicker">World renewable output in 2023</text>
  <text x="40" y="96" class="chart-headline">Solar and wind supplied the visible acceleration.</text>
  {"".join(rects)}
  {"".join(labels)}
</svg>
"""


def build_country_chart(rows: list[dict]) -> str:
    rows = [row for row in rows if row["country"] != "World"]
    bars = []
    labels = []
    for idx, row in enumerate(rows):
        y = 48 + idx * 62
        renewable = float(row["renewables_share_elec_pct"])
        fossil = float(row["fossil_share_elec_pct"])
        bars.append(
            f'<rect x="250" y="{y}" width="{renewable * 5.4:.1f}" height="20" rx="10" fill="#b9ff63"></rect>'
        )
        bars.append(
            f'<rect x="250" y="{y + 24}" width="{fossil * 5.4:.1f}" height="16" rx="8" fill="#39574e"></rect>'
        )
        labels.append(
            f'<text x="40" y="{y + 16}" class="country-label">{row["country"]}</text>'
            f'<text x="260" y="{y + 16}" class="bar-value">{renewable:.1f}% renewable</text>'
            f'<text x="260" y="{y + 38}" class="bar-value fossil">{fossil:.1f}% fossil</text>'
        )
    return f"""
<svg viewBox="0 0 900 360" class="chart" aria-labelledby="country-title" role="img" data-chart-id="country_compare_bars">
  <title id="country-title">Country comparison of renewable and fossil electricity shares in 2023</title>
  <rect x="0" y="0" width="900" height="360" rx="24" fill="#10231d"></rect>
  <text x="40" y="34" class="chart-kicker">2023 comparison across selected markets</text>
  {"".join(bars)}
  {"".join(labels)}
</svg>
"""


def source_chip(source: dict) -> str:
    return (
        f'<a class="source-chip" data-source-id="{source["source_id"]}" '
        f'href="{source["canonical_url"]}">{source["short_label"]}</a>'
    )


def build_preview_html(preset_name: str, background: str, foreground: str, summary: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{preset_name} Preview</title>
  <style>
    html, body {{
      margin: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: {background};
      color: {foreground};
      font-family: "Trebuchet MS", Arial, sans-serif;
    }}
    .slide {{
      width: 100vw;
      height: 100vh;
      height: 100dvh;
      overflow: hidden;
      display: grid;
      place-items: center;
      padding: 4vw;
      box-sizing: border-box;
    }}
    .card {{
      width: min(72vw, 980px);
      border: 1px solid rgba(255,255,255,0.15);
      border-radius: 28px;
      padding: 32px;
      background: rgba(255,255,255,0.06);
      backdrop-filter: blur(8px);
    }}
    h1 {{
      margin: 0 0 16px;
      font-size: clamp(2rem, 4vw, 4rem);
      line-height: 0.94;
    }}
    p {{
      margin: 0;
      font-size: clamp(1rem, 1.5vw, 1.3rem);
      line-height: 1.45;
      max-width: 48ch;
    }}
    .eyebrow {{
      margin-bottom: 12px;
      text-transform: uppercase;
      letter-spacing: 0.16em;
      font-size: 0.82rem;
      opacity: 0.78;
    }}
  </style>
</head>
<body data-preset="{preset_name}">
  <main class="slide">
    <section class="card">
      <div class="eyebrow">Preview direction</div>
      <h1>{preset_name}</h1>
      <p>{summary}</p>
    </section>
  </main>
</body>
</html>"""


def write_previews() -> list[str]:
    PREVIEW_ROOT.mkdir(parents=True, exist_ok=True)
    for existing in PREVIEW_ROOT.glob("*.html"):
        existing.unlink()
    preset_names = []
    for index, (preset_name, background, foreground, summary) in enumerate(PRESET_EXPLORATIONS, start=1):
        preview_html = build_preview_html(preset_name, background, foreground, summary)
        (PREVIEW_ROOT / f"{index:02d}-{slugify(preset_name)}.html").write_text(
            preview_html,
            encoding="utf-8",
        )
        preset_names.append(preset_name)
    return preset_names


def build_html(
    brief: dict,
    notes: dict,
    world_rows: list[dict],
    country_rows: list[dict],
    mix_rows: list[dict],
    resolved_sources: dict[str, dict],
) -> str:
    latest = world_rows[-1]
    w2014 = world_rows[0]
    brand_mark = (DATA_ROOT / "assets/brand-mark.svg").read_text(encoding="utf-8")
    grid_pattern = (DATA_ROOT / "assets/grid-pattern.svg").read_text(encoding="utf-8")
    line_chart = build_line_chart(world_rows)
    mix_chart = build_mix_chart(latest)
    country_chart = build_country_chart(mix_rows)

    summary_cards = [
        f'<article class="summary-card"><span class="card-kicker">Scale</span><strong>{fmt_num(float(latest["renewables_electricity_twh"]), 0)} TWh</strong><p>World renewable electricity in 2023.</p></article>',
        f'<article class="summary-card"><span class="card-kicker">Share</span><strong>{fmt_num(float(latest["renewables_share_elec_pct"]))}%</strong><p>Of global electricity generation in 2023.</p></article>',
        f'<article class="summary-card"><span class="card-kicker">Solar</span><strong>{fmt_num(float(latest["solar_electricity_twh"]), 0)} TWh</strong><p>Fastest visible expansion since 2014.</p></article>',
        f'<article class="summary-card"><span class="card-kicker">Wind</span><strong>{fmt_num(float(latest["wind_electricity_twh"]), 0)} TWh</strong><p>Still essential to system-level growth.</p></article>',
    ]
    country_highlights = []
    highlight_countries = {"Brazil", "Germany", "China"}
    for row in mix_rows:
        if row["country"] == "World":
            continue
        if row["country"] not in highlight_countries:
            continue
        country_highlights.append(
            f"<li><strong>{row['country']}</strong>: {fmt_num(float(row['renewables_share_elec_pct']))}% renewable share; "
            f"{fmt_num(float(row['solar_share_elec_pct']))}% solar, {fmt_num(float(row['wind_share_elec_pct']))}% wind, {fmt_num(float(row['hydro_share_elec_pct']))}% hydro.</li>"
        )
    sources_slide = "".join(
        "<li>"
        f"<strong>{source['short_label']}</strong> - "
        f'<a data-source-id="{source["source_id"]}" href="{source["canonical_url"]}">{source["canonical_url"]}</a>'
        "</li>"
        for source in resolved_sources.values()
    )
    cover_sources = source_chip(resolved_sources["owid-energy-data"])
    risk_sources = "".join(
        source_chip(resolved_sources[source_id])
        for source_id in [
            "iea-tripling-2030",
            "iea-pledge-update-2025",
            "irena-capacity-stats-2025",
        ]
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{brief['deck_title']}</title>
  <style>
    :root {{
      --bg: #071411;
      --paper: #f5f0e6;
      --panel: #10231d;
      --panel-2: #173229;
      --ink: #f6f1e6;
      --ink-muted: rgba(246, 241, 230, 0.78);
      --ink-dark: #10231d;
      --lime: #b9ff63;
      --mint: #7fe4c3;
      --blue: #71a7ff;
      --stroke: rgba(246, 241, 230, 0.16);
      --shadow: 0 24px 80px rgba(0, 0, 0, 0.28);
      --motion-ms: 160ms;
    }}
    @media (prefers-reduced-motion: reduce) {{
      :root {{ --motion-ms: 0ms; }}
      * {{
        animation-duration: 0ms !important;
        transition-duration: 0ms !important;
        scroll-behavior: auto !important;
      }}
    }}
    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background:
        radial-gradient(circle at top left, rgba(185,255,99,0.10), transparent 28%),
        radial-gradient(circle at bottom right, rgba(113,167,255,0.12), transparent 24%),
        linear-gradient(180deg, #06100d 0%, #0b1a16 100%);
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
    }}
    body {{
      min-height: 100vh;
      min-height: 100dvh;
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      background-image: url("data:image/svg+xml;utf8,{grid_pattern.replace("#", "%23").replace("\n", "")}");
      opacity: 0.18;
      pointer-events: none;
    }}
    .deck {{
      position: relative;
      width: 100%;
      height: 100vh;
      height: 100dvh;
      overflow: hidden;
    }}
    .slide {{
      position: absolute;
      inset: 0;
      display: grid;
      grid-template-columns: 1fr;
      align-content: stretch;
      padding: clamp(18px, 2.6vw, 32px);
      opacity: 0;
      transform: translateX(4vw) scale(0.985);
      transition:
        opacity var(--motion-ms) ease,
        transform var(--motion-ms) ease;
      pointer-events: none;
      overflow: hidden;
    }}
    .slide.is-active {{
      opacity: 1;
      transform: none;
      pointer-events: auto;
      z-index: 2;
    }}
    .frame {{
      position: relative;
      display: grid;
      grid-template-rows: auto 1fr auto;
      gap: clamp(10px, 1.8vh, 18px);
      width: 100%;
      height: 100%;
      min-height: 0;
      padding: clamp(16px, 2.2vw, 28px);
      border: 1px solid var(--stroke);
      border-radius: 28px;
      background:
        linear-gradient(180deg, rgba(16,35,29,0.92) 0%, rgba(8,17,14,0.96) 100%);
      box-shadow: var(--shadow);
      overflow: hidden;
    }}
    .slide-head {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
    }}
    .eyebrow {{
      margin: 0 0 10px;
      color: var(--lime);
      text-transform: uppercase;
      letter-spacing: 0.16em;
      font-size: clamp(11px, 1vw, 14px);
      font-family: "Trebuchet MS", Arial, sans-serif;
      font-weight: 800;
    }}
    h1, h2, h3, p, li {{
      margin: 0;
    }}
    h1 {{
      font-size: clamp(2.6rem, 5vw, 5.8rem);
      line-height: 0.94;
      max-width: 10ch;
      letter-spacing: -0.04em;
    }}
    h2 {{
      font-size: clamp(1.6rem, 3vw, 3.1rem);
      line-height: 1.02;
      letter-spacing: -0.03em;
      max-width: 16ch;
    }}
    .lede, .body-copy, li, .mini-note, .bar-value {{
      font-family: "Trebuchet MS", Arial, sans-serif;
    }}
    .lede {{
      font-size: clamp(1rem, 1.35vw, 1.35rem);
      line-height: 1.42;
      color: var(--ink-muted);
      max-width: 62ch;
    }}
    .content-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.08fr) minmax(280px, 0.92fr);
      gap: clamp(12px, 2vw, 24px);
      align-items: stretch;
      min-height: 0;
    }}
    .chart-wrap, .side-card, .summary-card, .sources-panel {{
      border-radius: 24px;
      border: 1px solid rgba(246,241,230,0.10);
      background: rgba(246,241,230,0.05);
      overflow: hidden;
    }}
    .chart-wrap {{
      padding: clamp(12px, 1.8vw, 18px);
      min-height: 0;
    }}
    .chart {{
      display: block;
      width: 100%;
      height: 100%;
      max-height: min(50vh, 430px);
    }}
    .chart-kicker {{
      fill: rgba(246,241,230,0.74);
      font-size: 16px;
      font-family: "Trebuchet MS", Arial, sans-serif;
      text-transform: uppercase;
      letter-spacing: 0.12em;
    }}
    .chart-headline {{
      fill: #f5f0e6;
      font-size: 28px;
    }}
    .segment-label, .country-label, .bar-value, .axis-label {{
      fill: #f5f0e6;
      font-size: 14px;
      font-family: "Trebuchet MS", Arial, sans-serif;
    }}
    .bar-value.fossil {{
      fill: rgba(246,241,230,0.7);
    }}
    .axis-label {{
      fill: rgba(246,241,230,0.62);
      text-anchor: middle;
    }}
    .side-card {{
      display: grid;
      grid-template-rows: auto auto 1fr auto;
      gap: 14px;
      padding: clamp(14px, 1.8vw, 20px);
      background: linear-gradient(180deg, rgba(185,255,99,0.10), rgba(113,167,255,0.08));
    }}
    .side-card strong, .summary-card strong {{
      font-size: clamp(1.45rem, 2vw, 2.5rem);
      line-height: 1;
    }}
    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: clamp(10px, 1.6vw, 16px);
      min-height: 0;
    }}
    .summary-card {{
      padding: clamp(14px, 1.8vw, 18px);
      display: grid;
      gap: 8px;
      align-content: start;
    }}
    .card-kicker {{
      color: var(--lime);
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 12px;
      font-family: "Trebuchet MS", Arial, sans-serif;
      font-weight: 800;
    }}
    .body-copy {{
      color: var(--ink-muted);
      font-size: clamp(0.98rem, 1.12vw, 1.18rem);
      line-height: 1.45;
    }}
    .bullet-list, .source-list {{
      display: grid;
      gap: 12px;
      padding-left: 18px;
      color: var(--ink-muted);
      font-size: clamp(0.96rem, 1.1vw, 1.12rem);
      line-height: 1.38;
    }}
    .source-list {{
      padding-left: 20px;
      font-size: clamp(0.82rem, 1vw, 0.98rem);
      line-height: 1.28;
    }}
    .source-list a {{
      color: var(--lime);
      text-decoration: none;
      overflow-wrap: anywhere;
    }}
    .source-chip {{
      display: inline-flex;
      align-items: center;
      margin: 6px 10px 0 0;
      padding: 7px 12px;
      border-radius: 999px;
      border: 1px solid rgba(246,241,230,0.16);
      background: rgba(246,241,230,0.06);
      color: var(--ink-muted);
      text-decoration: none;
      font-family: "Trebuchet MS", Arial, sans-serif;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    .footer-line {{
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 18px;
      color: rgba(246,241,230,0.72);
      font-family: "Trebuchet MS", Arial, sans-serif;
      font-size: 13px;
      min-height: 28px;
    }}
    .footer-left {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }}
    .footer-right {{
      flex: 0 0 auto;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .deck-nav {{
      position: fixed;
      left: 50%;
      bottom: 14px;
      transform: translateX(-50%);
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 16px;
      border-radius: 999px;
      border: 1px solid rgba(246,241,230,0.12);
      background: rgba(8,17,14,0.72);
      backdrop-filter: blur(18px);
      z-index: 5;
      font-family: "Trebuchet MS", Arial, sans-serif;
    }}
    .deck-nav button {{
      appearance: none;
      border: 0;
      width: 34px;
      height: 34px;
      border-radius: 999px;
      background: rgba(246,241,230,0.10);
      color: var(--ink);
      cursor: pointer;
      font-size: 18px;
      font-weight: 700;
    }}
    .progress-track {{
      width: clamp(120px, 20vw, 220px);
      height: 5px;
      border-radius: 999px;
      background: rgba(246,241,230,0.16);
      overflow: hidden;
    }}
    .progress-fill {{
      width: calc((var(--active-index) + 1) / 8 * 100%);
      height: 100%;
      background: linear-gradient(90deg, var(--lime), var(--mint));
      transition: width var(--motion-ms) ease;
    }}
    .mini-note {{
      color: rgba(246,241,230,0.66);
      font-size: 13px;
      line-height: 1.35;
    }}
    .cover-mark {{
      width: min(240px, 42vw);
      height: auto;
    }}
    .cover-logo {{
      width: min(240px, 42vw);
      flex: 0 0 auto;
    }}
    .cover-logo svg {{
      display: block;
      width: 100%;
      height: auto;
    }}
    .cover-stat {{
      font-size: clamp(2.4rem, 5vw, 4.8rem);
      line-height: 0.9;
    }}
    .cover-figure {{
      display: grid;
      gap: 6px;
    }}
    .tight-list {{
      display: grid;
      gap: 10px;
    }}
    [data-role="slide-main"] {{
      min-height: 0;
    }}
    @media (max-width: 900px) {{
      .content-grid {{
        grid-template-columns: 1fr;
      }}
      .chart {{
        max-height: min(34vh, 320px);
      }}
      .deck-nav {{
        width: calc(100vw - 24px);
        justify-content: center;
      }}
      .progress-track {{
        width: min(180px, 42vw);
      }}
    }}
    @media (max-width: 680px), (max-height: 740px) {{
      h1 {{
        font-size: clamp(2rem, 9vw, 3.2rem);
        max-width: 11ch;
      }}
      h2 {{
        font-size: clamp(1.3rem, 5.6vw, 2rem);
      }}
      .frame {{
        padding: 14px;
        gap: 10px;
      }}
      .chart {{
        max-height: min(28vh, 220px);
      }}
      .summary-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
      }}
      .summary-card {{
        padding: 12px;
      }}
      .summary-card strong {{
        font-size: 1.4rem;
      }}
      .source-list {{
        font-size: 0.78rem;
      }}
      .footer-line {{
        font-size: 11px;
      }}
    }}
    @media (max-height: 420px) and (orientation: landscape) {{
      .content-grid {{
        grid-template-columns: minmax(0, 1.12fr) minmax(200px, 0.88fr);
        gap: 10px;
      }}
      .slide-head {{
        gap: 8px;
      }}
      .eyebrow {{
        margin-bottom: 6px;
      }}
      h1 {{
        font-size: clamp(1.7rem, 4.1vw, 2.5rem);
        max-width: 13ch;
      }}
      .cover-logo {{
        width: 112px;
      }}
      .lede {{
        font-size: 0.8rem;
        line-height: 1.2;
      }}
      .body-copy, .bullet-list, .mini-note {{
        font-size: 0.76rem;
        line-height: 1.18;
      }}
      .cover-stat {{
        font-size: 1.65rem;
      }}
      .side-card {{
        gap: 8px;
        padding: 10px 12px;
      }}
      .tight-list {{
        gap: 6px;
      }}
      .source-chip {{
        margin: 4px 6px 0 0;
        padding: 5px 8px;
        font-size: 10px;
      }}
      .frame {{
        gap: 8px;
      }}
      .footer-line {{
        min-height: 22px;
        font-size: 10px;
      }}
    }}
  </style>
</head>
<body style="--active-index:0" data-active-slide="0" data-preset="{CHOSEN_PRESET}">
  <main class="deck" aria-label="Presentation deck">
    <section class="slide is-active" data-slide data-slide-index="0" id="slide-cover">
      <div class="frame">
        <header class="slide-head">
          <div>
            <p class="eyebrow">Quarterly executive briefing</p>
            <h1>Renewable expansion is real. Execution quality is now the harder differentiator.</h1>
          </div>
          <div class="cover-logo" aria-hidden="true">{brand_mark}</div>
        </header>
        <div class="content-grid" data-role="slide-main">
          <div class="chart-wrap">
            <div class="tight-list">
              <p class="lede">{brief['key_messages'][0]}</p>
              <p class="lede">{brief['key_messages'][1]}</p>
              <p class="body-copy">This deck links growth, mix shifts, country divergence, and delivery constraints into one management view.</p>
            </div>
          </div>
          <aside class="side-card">
            <span class="card-kicker">2023 world output</span>
            <strong class="cover-stat">{fmt_num(float(latest['renewables_electricity_twh']), 0)} TWh</strong>
            <div class="cover-figure">
              <p class="body-copy">Renewables supplied {fmt_num(float(latest['renewables_share_elec_pct']))}% of global electricity generation in 2023.</p>
              <p class="mini-note">2014 baseline: {fmt_num(float(w2014['renewables_share_elec_pct']))}% share.</p>
            </div>
            <div>{cover_sources}</div>
          </aside>
        </div>
        <footer class="footer-line">
          <div class="footer-left"><span>Management-ready offline HTML deck</span></div>
          <div class="footer-right">1 / 8</div>
        </footer>
      </div>
    </section>

    <section class="slide" data-slide data-slide-index="1" id="slide-summary" aria-hidden="true">
      <div class="frame">
        <header class="slide-head">
          <div>
            <p class="eyebrow">Executive summary</p>
            <h2>Momentum improved, but system delivery now matters as much as the generation headline.</h2>
          </div>
        </header>
        <div class="summary-grid" data-role="slide-main">
          {"".join(summary_cards)}
        </div>
        <footer class="footer-line">
          <div class="footer-left">
            {source_chip(resolved_sources["owid-energy-data"])}
            {source_chip(resolved_sources["iea-pledge-update-2025"])}
          </div>
          <div class="footer-right">2 / 8</div>
        </footer>
      </div>
    </section>

    <section class="slide" data-slide data-slide-index="2" id="slide-growth" aria-hidden="true">
      <div class="frame">
        <header class="slide-head">
          <div>
            <p class="eyebrow">Overall growth</p>
            <h2>Renewable electricity added roughly {fmt_num(float(latest['renewables_electricity_twh']) - float(w2014['renewables_electricity_twh']), 0)} TWh between 2014 and 2023.</h2>
          </div>
        </header>
        <div class="content-grid" data-role="slide-main">
          <div class="chart-wrap">{line_chart}</div>
          <aside class="side-card">
            <span class="card-kicker">Interpretation</span>
            <p class="body-copy">The line keeps steepening from a higher base. That is why executive attention can move from proving demand to understanding which execution constraints now control realized value.</p>
            <p class="mini-note">From {fmt_num(float(w2014['renewables_share_elec_pct']))}% share in 2014 to {fmt_num(float(latest['renewables_share_elec_pct']))}% in 2023.</p>
          </aside>
        </div>
        <footer class="footer-line">
          <div class="footer-left">{source_chip(resolved_sources["owid-energy-data"])}</div>
          <div class="footer-right">3 / 8</div>
        </footer>
      </div>
    </section>

    <section class="slide" data-slide data-slide-index="3" id="slide-mix" aria-hidden="true">
      <div class="frame">
        <header class="slide-head">
          <div>
            <p class="eyebrow">Structure change</p>
            <h2>Solar and wind drove the visible mix shift, while hydro stayed large but much steadier.</h2>
          </div>
        </header>
        <div class="content-grid" data-role="slide-main">
          <div class="chart-wrap">{mix_chart}</div>
          <aside class="side-card">
            <span class="card-kicker">Why it matters</span>
            <p class="body-copy">The next management question is not only where capacity is announced, but where networks, storage, and permitting keep pace with the technologies that are growing fastest.</p>
            <p class="mini-note">Solar: {fmt_num(float(latest['solar_electricity_twh']), 0)} TWh. Wind: {fmt_num(float(latest['wind_electricity_twh']), 0)} TWh. Hydro: {fmt_num(float(latest['hydro_electricity_twh']), 0)} TWh.</p>
          </aside>
        </div>
        <footer class="footer-line">
          <div class="footer-left">{source_chip(resolved_sources["owid-energy-data"])}</div>
          <div class="footer-right">4 / 8</div>
        </footer>
      </div>
    </section>

    <section class="slide" data-slide data-slide-index="4" id="slide-country" aria-hidden="true">
      <div class="frame">
        <header class="slide-head">
          <div>
            <p class="eyebrow">Country comparison</p>
            <h2>Scale leaders and high-share systems are not interchangeable stories.</h2>
          </div>
        </header>
        <div class="content-grid" data-role="slide-main">
          <div class="chart-wrap">{country_chart}</div>
          <aside class="side-card">
            <span class="card-kicker">Read-through</span>
            <ul class="bullet-list">
              {"".join(country_highlights)}
            </ul>
          </aside>
        </div>
        <footer class="footer-line">
          <div class="footer-left">{source_chip(resolved_sources["owid-energy-data"])}</div>
          <div class="footer-right">5 / 8</div>
        </footer>
      </div>
    </section>

    <section class="slide" data-slide data-slide-index="5" id="slide-risks" aria-hidden="true">
      <div class="frame">
        <header class="slide-head">
          <div>
            <p class="eyebrow">Constraints and risks</p>
            <h2>Delivery bottlenecks have moved closer to the grid, pipeline, and financing layers.</h2>
          </div>
        </header>
        <div class="content-grid" data-role="slide-main">
          <div class="sources-panel" style="padding: clamp(14px, 1.8vw, 20px);">
            <ul class="bullet-list">
              {"".join(f"<li>{item}</li>" for item in notes["risk_points"])}
            </ul>
          </div>
          <aside class="side-card">
            <span class="card-kicker">Strategic frame</span>
            <p class="body-copy">The implication is not simply slower projects. It is higher variance in when and where announced ambition converts into operational output and value capture.</p>
            <p class="mini-note">These constraints appear consistently across IEA and IRENA framing in the local source catalog.</p>
          </aside>
        </div>
        <footer class="footer-line">
          <div class="footer-left">{risk_sources}</div>
          <div class="footer-right">6 / 8</div>
        </footer>
      </div>
    </section>

    <section class="slide" data-slide data-slide-index="6" id="slide-actions" aria-hidden="true">
      <div class="frame">
        <header class="slide-head">
          <div>
            <p class="eyebrow">Action implications</p>
            <h2>Track execution quality as carefully as capacity growth.</h2>
          </div>
        </header>
        <div class="content-grid" data-role="slide-main">
          <div class="sources-panel" style="padding: clamp(14px, 1.8vw, 20px);">
            <ul class="bullet-list">
              {"".join(f"<li>{item}</li>" for item in notes["action_implications"])}
            </ul>
          </div>
          <aside class="side-card">
            <span class="card-kicker">Management use</span>
            <p class="body-copy">Use the mix of global trend, country comparison, and risk framing to separate demand momentum from power-system readiness when allocating attention or capital.</p>
            <p class="mini-note">Keep the story short: one claim, one chart, a small evidence set.</p>
          </aside>
        </div>
        <footer class="footer-line">
          <div class="footer-left">{source_chip(resolved_sources["iea-pledge-update-2025"])}{source_chip(resolved_sources["owid-energy-data"])}</div>
          <div class="footer-right">7 / 8</div>
        </footer>
      </div>
    </section>

    <section class="slide" data-slide data-slide-index="7" id="slide-sources" aria-hidden="true">
      <div class="frame">
        <header class="slide-head">
          <div>
            <p class="eyebrow">Sources</p>
            <h2>Local registry references used in this deck</h2>
          </div>
        </header>
        <div class="sources-panel" style="padding: clamp(14px, 1.8vw, 20px);" data-role="slide-main">
          <ol class="source-list">{sources_slide}</ol>
        </div>
        <footer class="footer-line">
          <div class="footer-left"><span>All links resolved through the local source registry.</span></div>
          <div class="footer-right">8 / 8</div>
        </footer>
      </div>
    </section>
  </main>

  <nav class="deck-nav" aria-label="Slide controls">
    <button type="button" id="prev-button" aria-label="Previous slide">‹</button>
    <div class="progress-track" data-progress><div class="progress-fill" id="progress-indicator"></div></div>
    <span id="progress-text">1 / 8</span>
    <button type="button" id="next-button" aria-label="Next slide">›</button>
  </nav>

  <script>
    class PresentationController {{
      constructor() {{
        this.slides = Array.from(document.querySelectorAll('[data-slide]'));
        this.index = 0;
        this.touchStartX = null;
        this.touchStartY = null;
        this.progressText = document.getElementById('progress-text');
        document.body.setAttribute('tabindex', '-1');
        this.syncFromHash();
        this.bind();
        this.render();
        document.body.focus();
      }}

      bind() {{
        window.addEventListener('hashchange', () => this.syncFromHash());
        document.getElementById('next-button').addEventListener('click', () => this.go(1));
        document.getElementById('prev-button').addEventListener('click', () => this.go(-1));
        const handleKeyDown = (event) => {{
          if (['ArrowRight', 'PageDown', ' '].includes(event.key)) {{
            event.preventDefault();
            this.go(1);
          }}
          if (['ArrowLeft', 'PageUp'].includes(event.key)) {{
            event.preventDefault();
            this.go(-1);
          }}
          if (event.key === 'Home') {{
            event.preventDefault();
            this.setIndex(0);
          }}
          if (event.key === 'End') {{
            event.preventDefault();
            this.setIndex(this.slides.length - 1);
          }}
        }};
        window.addEventListener('keydown', handleKeyDown, {{ passive: false }});
        document.addEventListener('keydown', handleKeyDown, {{ passive: false }});

        let wheelLock = false;
        window.addEventListener('wheel', (event) => {{
          if (Math.abs(event.deltaY) < 8) return;
          event.preventDefault();
          if (wheelLock) return;
          wheelLock = true;
          this.go(event.deltaY > 0 ? 1 : -1);
          window.setTimeout(() => {{ wheelLock = false; }}, 240);
        }}, {{ passive: false }});

        window.addEventListener('touchstart', (event) => {{
          const touch = event.changedTouches[0];
          this.touchStartX = touch.clientX;
          this.touchStartY = touch.clientY;
        }}, {{ passive: true }});

        window.addEventListener('touchend', (event) => {{
          if (this.touchStartX === null || this.touchStartY === null) return;
          const touch = event.changedTouches[0];
          const deltaX = touch.clientX - this.touchStartX;
          const deltaY = touch.clientY - this.touchStartY;
          if (Math.abs(deltaX) > 36 && Math.abs(deltaX) > Math.abs(deltaY)) {{
            this.go(deltaX < 0 ? 1 : -1);
          }}
          this.touchStartX = null;
          this.touchStartY = null;
        }}, {{ passive: true }});
      }}

      syncFromHash() {{
        const hash = window.location.hash.replace('#', '');
        const match = this.slides.findIndex((slide) => slide.id === hash);
        if (match >= 0) {{
          this.index = match;
        }}
      }}

      setIndex(nextIndex) {{
        this.index = Math.max(0, Math.min(this.slides.length - 1, nextIndex));
        const slide = this.slides[this.index];
        history.replaceState(null, '', '#' + slide.id);
        this.render();
      }}

      go(delta) {{
        this.setIndex(this.index + delta);
      }}

      render() {{
        this.slides.forEach((slide, idx) => {{
          const active = idx === this.index;
          slide.classList.toggle('is-active', active);
          slide.setAttribute('aria-hidden', active ? 'false' : 'true');
        }});
        document.body.dataset.activeSlide = String(this.index);
        document.body.style.setProperty('--active-index', String(this.index));
        this.progressText.textContent = `${{this.index + 1}} / ${{this.slides.length}}`;
      }}
    }}

    window.presentationController = new PresentationController();
  </script>
</body>
</html>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    explored_presets = write_previews()

    brief = read_json(DATA_ROOT / "brief/briefing_requirements.json")
    notes = read_json(DATA_ROOT / "brief/editorial_notes.json")
    world_rows = read_csv(DATA_ROOT / "series/global_renewables_2014_2023.csv")
    country_rows = read_csv(DATA_ROOT / "series/country_renewables_share_2019_2023.csv")
    mix_rows = read_csv(DATA_ROOT / "series/country_mix_2023.csv")

    source_ids = brief["source_requirements"]["required_source_ids"]
    resolved_list = resolve_sources(source_ids)
    resolved_sources = {item["source_id"]: item for item in resolved_list}

    html = build_html(brief, notes, world_rows, country_rows, mix_rows, resolved_sources)
    (output_dir / "presentation.html").write_text(html, encoding="utf-8")

    slides = [
        ("slide-cover", "Cover", [], ["owid-energy-data"]),
        ("slide-summary", "Executive Summary", [], ["owid-energy-data", "iea-pledge-update-2025"]),
        ("slide-growth", "Overall Growth", ["global_growth_line"], ["owid-energy-data"]),
        ("slide-mix", "Mix Shift", ["mix_shift_stack"], ["owid-energy-data"]),
        ("slide-country", "Country Comparison", ["country_compare_bars"], ["owid-energy-data"]),
        ("slide-risks", "Constraints and Risks", [], ["iea-tripling-2030", "iea-pledge-update-2025", "irena-capacity-stats-2025"]),
        ("slide-actions", "Action Implications", [], ["owid-energy-data", "iea-pledge-update-2025"]),
        ("slide-sources", "Sources", [], source_ids),
    ]
    manifest = {
        "deck_title": brief["deck_title"],
        "slide_count": len(slides),
        "slides": [
            {
                "slide_id": slide_id,
                "title": title,
                "primary_message": {
                    "slide-cover": "Execution quality now matters as much as growth momentum.",
                    "slide-summary": "Momentum improved, but system constraints determine realized value.",
                    "slide-growth": "World renewable electricity grew materially from 2014 to 2023.",
                    "slide-mix": "Solar and wind drove the most visible change in the mix.",
                    "slide-country": "Scale and share tell different country stories.",
                    "slide-risks": "Grid, permitting, and financing bottlenecks shape delivery risk.",
                    "slide-actions": "Track execution quality alongside ambition.",
                    "slide-sources": "All references resolve through the local registry.",
                }[slide_id],
                "visuals_used": {
                    "slide-cover": ["brand-mark.svg", "metric-card"],
                    "slide-summary": ["summary-cards"],
                    "slide-growth": ["global_growth_line"],
                    "slide-mix": ["mix_shift_stack"],
                    "slide-country": ["country_compare_bars"],
                    "slide-risks": ["risk-list"],
                    "slide-actions": ["action-list"],
                    "slide-sources": ["source-list"],
                }[slide_id],
                "chart_ids": chart_ids,
                "source_ids": source_ids_for_slide,
            }
            for slide_id, title, chart_ids, source_ids_for_slide in slides
        ],
        "data_files_used": [
            "global_renewables_2014_2023.csv",
            "country_renewables_share_2019_2023.csv",
            "country_mix_2023.csv",
        ],
        "asset_files_used": ["brand-mark.svg", "grid-pattern.svg"],
        "source_ids_used": source_ids,
        "viewport_targets": brief["viewport_targets"],
        "design_notes": (
            f"Chosen preset: {CHOSEN_PRESET}. "
            f"Explored directions: {', '.join(explored_presets)}. "
            "Editorial dark-on-paper deck with full-viewport slides, restrained motion, "
            "inline SVG charts, and consistent citation chips."
        ),
    }
    (output_dir / "presentation_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    source_audit = {
        "registry_endpoint": REGISTRY,
        "registry_checked": True,
        "sources_resolved": [
            {
                "source_id": source["source_id"],
                "short_label": source["short_label"],
                "canonical_url": source["canonical_url"],
            }
            for source in resolved_list
        ],
        "slide_source_map": {
            slide_id: source_ids_for_slide for slide_id, _, _, source_ids_for_slide in slides
        },
        "notes": [
            "Build verified the local source registry health endpoint before resolving required source ids.",
            "All citations in the final deck use registry-backed source ids."
        ],
    }
    (output_dir / "source_audit.json").write_text(
        json.dumps(source_audit, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
