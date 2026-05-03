#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/root/environment/data"))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def make_html(brief: dict, sources: dict, world_rows: list[dict], mix_rows: list[dict]) -> str:
    latest = world_rows[-1]
    source_items = sources["sources"]
    source_links = "".join(
        f'<li><a href="{item["canonical_url"]}">{item["short_label"]}</a> - {item["title"]}</li>'
        for item in source_items
    )
    country_rows = "".join(
        "<tr>"
        f"<td>{row['country']}</td>"
        f"<td>{float(row['renewables_share_elec_pct']):.1f}%</td>"
        f"<td>{float(row['fossil_share_elec_pct']):.1f}%</td>"
        "</tr>"
        for row in mix_rows
    )
    points = " ".join(
        f"{40 + idx * 90},{360 - float(row['renewables_electricity_twh']) / 30}"
        for idx, row in enumerate(world_rows)
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{brief['deck_title']}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #f4f0e8;
      --card: #ffffff;
      --ink: #0f1d1a;
      --muted: #61706a;
      --accent: #187f5a;
      --accent-soft: #dff8cf;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, sans-serif;
      background: var(--bg);
      color: var(--ink);
      line-height: 1.4;
    }}
    nav {{
      position: sticky;
      top: 0;
      background: rgba(244, 240, 232, 0.96);
      backdrop-filter: blur(18px);
      border-bottom: 1px solid rgba(15, 29, 26, 0.08);
      display: flex;
      gap: 12px;
      padding: 16px 24px;
      z-index: 100;
      overflow-x: auto;
    }}
    nav a {{
      color: var(--ink);
      text-decoration: none;
      white-space: nowrap;
      font-weight: 700;
    }}
    main {{
      width: min(1200px, calc(100vw - 48px));
      margin: 0 auto;
      padding: 32px 0 64px;
    }}
    .slide {{
      background: var(--card);
      border-radius: 28px;
      padding: 48px;
      margin-bottom: 28px;
      box-shadow: 0 16px 60px rgba(15, 29, 26, 0.08);
    }}
    .eyebrow {{ color: var(--accent); font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; }}
    h1, h2 {{ margin: 0 0 18px; line-height: 1.02; }}
    h1 {{ font-size: 72px; max-width: 10ch; }}
    h2 {{ font-size: 42px; }}
    p, li, td, th {{ font-size: 19px; }}
    .hero-grid, .two-col {{
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 24px;
      align-items: start;
    }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
      margin-top: 24px;
    }}
    .summary article {{
      background: var(--accent-soft);
      padding: 18px;
      border-radius: 18px;
    }}
    .chart-card {{
      background: linear-gradient(180deg, #f7fff4, #edf5eb);
      border-radius: 22px;
      padding: 16px;
    }}
    .source-chip {{
      display: inline-block;
      margin: 6px 8px 0 0;
      padding: 7px 10px;
      border-radius: 999px;
      background: #eef2ef;
      color: var(--muted);
      text-decoration: none;
      font-size: 13px;
    }}
    table {{ width: 100%; border-collapse: collapse; }}
    td, th {{ padding: 10px; border-bottom: 1px solid #e6ece7; text-align: left; }}
    ul {{ margin: 0; padding-left: 22px; }}
    footer {{ margin-top: 20px; color: var(--muted); font-size: 14px; }}
    @media (max-width: 900px) {{
      main {{ width: calc(100vw - 24px); }}
      .slide {{ padding: 26px; }}
      .hero-grid, .two-col, .summary {{ grid-template-columns: 1fr; }}
      h1 {{ font-size: 56px; }}
      h2 {{ font-size: 34px; }}
    }}
  </style>
</head>
<body>
  <nav>
    <a href="#slide-cover">Cover</a>
    <a href="#slide-summary">Summary</a>
    <a href="#slide-growth">Growth</a>
    <a href="#slide-mix">Mix</a>
    <a href="#slide-country">Countries</a>
    <a href="#slide-risks">Risks</a>
    <a href="#slide-actions">Actions</a>
    <a href="#slide-sources">Sources</a>
  </nav>
  <main>
    <section id="slide-cover" class="slide">
      <div class="hero-grid">
        <div>
          <div class="eyebrow">Quarterly briefing</div>
          <h1>Global renewable expansion is broad, but execution still determines who captures value.</h1>
          <p>{brief['key_messages'][1]}</p>
        </div>
        <div class="chart-card">
          <img src="../data/assets/brand-mark.svg" alt="Renewables Brief mark" style="max-width:100%;height:auto;">
          <p><strong>2023 world renewable electricity</strong></p>
          <p style="font-size:64px;margin:0;">{float(latest['renewables_electricity_twh']):.0f}</p>
          <p>TWh generated</p>
          <a class="source-chip" href="{source_items[0]['canonical_url']}">{source_items[0]['short_label']}</a>
        </div>
      </div>
    </section>
    <section id="slide-summary" class="slide">
      <div class="eyebrow">Executive summary</div>
      <h2>Momentum improved, but delivery constraints now matter more than headline ambition.</h2>
      <div class="summary">
        <article><strong>{brief['key_messages'][0]}</strong><p>Growth is not just larger; it is compounding from a higher base.</p></article>
        <article><strong>{brief['key_messages'][2]}</strong><p>Solar is now the fastest-expanding piece of the global mix story.</p></article>
        <article><strong>{brief['key_messages'][3]}</strong><p>Wind remains material, but the pace of execution still varies by market.</p></article>
        <article><strong>Country stories diverge.</strong><p>Scale leaders and high-share systems are not always the same markets.</p></article>
      </div>
    </section>
    <section id="slide-growth" class="slide">
      <div class="eyebrow">Overall growth</div>
      <h2>Renewable electricity added nearly 3.7 PWh between 2014 and 2023.</h2>
      <div class="chart-card">
        <svg viewBox="0 0 900 420" width="100%" height="360" role="img" aria-label="World renewable electricity trend">
          <rect x="0" y="0" width="900" height="420" fill="#f7fff4"></rect>
          <polyline fill="none" stroke="#187f5a" stroke-width="5" points="{points}"></polyline>
        </svg>
      </div>
      <p>The same trend line also captures why the next discussion has shifted from momentum proof to systems integration and execution quality.</p>
      <footer><a class="source-chip" href="{source_items[0]['canonical_url']}">{source_items[0]['short_label']}</a></footer>
    </section>
    <section id="slide-mix" class="slide">
      <div class="eyebrow">Structure change</div>
      <h2>Solar and wind drove most of the visible mix shift, while hydro stayed large but comparatively stable.</h2>
      <div class="two-col">
        <div class="chart-card">
          <p><strong>2023 world renewable stack</strong></p>
          <ul>
            <li>Solar: {float(latest['solar_electricity_twh']):.0f} TWh</li>
            <li>Wind: {float(latest['wind_electricity_twh']):.0f} TWh</li>
            <li>Hydro: {float(latest['hydro_electricity_twh']):.0f} TWh</li>
          </ul>
        </div>
        <div>
          <p>That pattern matters for executives because the integration requirements for incremental solar and wind are different from the legacy hydro footprint already in the system.</p>
          <p>Buildout pressure therefore shifts from merely adding generation to coordinating networks, storage, permitting, and delivery sequencing.</p>
        </div>
      </div>
      <footer><a class="source-chip" href="{source_items[0]['canonical_url']}">{source_items[0]['short_label']}</a></footer>
    </section>
    <section id="slide-country" class="slide">
      <div class="eyebrow">Country comparison</div>
      <h2>Country positions differ sharply depending on whether the lens is absolute scale or share of electricity.</h2>
      <table>
        <thead><tr><th>Country</th><th>Renewables share</th><th>Fossil share</th></tr></thead>
        <tbody>{country_rows}</tbody>
      </table>
      <p>Brazil and Germany show why higher shares can coexist with very different systems; China and the United States show why scale leadership does not automatically imply the highest share of mix.</p>
      <footer><a class="source-chip" href="{source_items[0]['canonical_url']}">{source_items[0]['short_label']}</a></footer>
    </section>
    <section id="slide-risks" class="slide">
      <div class="eyebrow">Constraints and risks</div>
      <h2>Execution risk has moved closer to the grid, pipeline, and financing layers.</h2>
      <ul>
        <li>Transmission and interconnection bottlenecks slow the conversion of announced projects into delivered output.</li>
        <li>Permitting remains uneven across markets, stretching timelines even where investor appetite is strong.</li>
        <li>Supply-chain, labor, and financing conditions continue to create delivery variance across markets and technologies.</li>
      </ul>
      <p>These are strategy issues, not just engineering details, because they change timing, geography, and return profiles.</p>
      <footer>
        <a class="source-chip" href="{source_items[1]['canonical_url']}">{source_items[1]['short_label']}</a>
        <a class="source-chip" href="{source_items[2]['canonical_url']}">{source_items[2]['short_label']}</a>
        <a class="source-chip" href="{source_items[3]['canonical_url']}">{source_items[3]['short_label']}</a>
      </footer>
    </section>
    <section id="slide-actions" class="slide">
      <div class="eyebrow">Action implications</div>
      <h2>Watch execution quality, not just headline capacity ambition.</h2>
      <ol>
        <li>Track delivery bottlenecks as seriously as generation additions.</li>
        <li>Separate technology momentum from power-system readiness.</li>
        <li>Use country comparisons to avoid over-reading one metric as the whole story.</li>
      </ol>
      <p>Teams that distinguish scale, share, and integration readiness will make better allocation decisions than teams that treat them as interchangeable.</p>
    </section>
    <section id="slide-sources" class="slide">
      <div class="eyebrow">Sources</div>
      <h2>Reference links used in this briefing</h2>
      <ul>{source_links}</ul>
    </section>
  </main>
</body>
</html>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    brief = read_json(DATA_ROOT / "brief/briefing_requirements.json")
    world_rows = read_csv(DATA_ROOT / "series/global_renewables_2014_2023.csv")
    mix_rows = read_csv(DATA_ROOT / "series/country_mix_2023.csv")
    sources = read_json(DATA_ROOT / "sources/source_catalog.json")

    presentation_html = make_html(brief, sources, world_rows, mix_rows)
    (output_dir / "presentation.html").write_text(presentation_html, encoding="utf-8")

    manifest = {
        "deck_title": brief["deck_title"],
        "slide_count": 8,
        "slides": [
            {
                "slide_id": "slide-cover",
                "title": title,
                "primary_message": title,
                "visuals_used": ["basic-card"],
                "chart_ids": [],
                "source_ids": [],
            }
            for title in brief["required_sections"]
        ],
        "data_files_used": [
            "global_renewables_2014_2023.csv",
            "country_mix_2023.csv",
        ],
        "asset_files_used": [
            "brand-mark.svg",
            "grid-pattern.svg",
        ],
        "source_ids_used": [item["source_id"] for item in sources["sources"]],
        "viewport_targets": brief["viewport_targets"],
        "design_notes": "Simple stacked briefing page with cards and charts.",
    }
    (output_dir / "presentation_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    source_audit = {
        "registry_endpoint": "http://127.0.0.1:4873",
        "registry_checked": False,
        "sources_resolved": [
            {
                "source_id": item["source_id"],
                "short_label": item["short_label"],
                "canonical_url": item["canonical_url"],
            }
            for item in sources["sources"]
        ],
        "slide_source_map": {
            "slide-growth": ["owid-energy-data"],
            "slide-mix": ["owid-energy-data"],
            "slide-country": ["owid-energy-data"],
            "slide-risks": [
                "iea-tripling-2030",
                "iea-pledge-update-2025",
                "irena-capacity-stats-2025",
            ],
        },
        "notes": ["Built from local files only."],
    }
    (output_dir / "source_audit.json").write_text(
        json.dumps(source_audit, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
