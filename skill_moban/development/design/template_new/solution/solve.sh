#!/bin/bash
set -euo pipefail

python3 - <<'PY'
from __future__ import annotations

import csv
import html
import json
from collections import Counter, defaultdict
from pathlib import Path

import requests


DATA = Path(__import__("os").environ.get("DATA_ROOT", "/root/data/briefing"))
OUT = Path(__import__("os").environ.get("OUTPUT_PATH", "/root/output/presentation.html"))
OUT.parent.mkdir(parents=True, exist_ok=True)

snapshot = json.loads((DATA / "operations_snapshot.json").read_text(encoding="utf-8"))
brand = json.loads((DATA / "brand_tokens.json").read_text(encoding="utf-8"))
with (DATA / "station_events.csv").open(encoding="utf-8") as handle:
    events = list(csv.DictReader(handle))
complaints = [
    json.loads(line)
    for line in (DATA / "customer_complaints.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
weather = requests.get("http://127.0.0.1:8111/api/weather-impact", timeout=3).json()
service_zones = requests.get("http://127.0.0.1:8111/api/service-zones", timeout=3).json()

colors = brand["colors"]
zone_availability = defaultdict(list)
zone_trips = defaultdict(int)
zone_dock = defaultdict(list)
for station in snapshot["stations"]:
    zone_availability[station["zone"]].append(station["avg_availability_pct"])
    zone_dock[station["zone"]].append(station["dock_balance_pct"])
    zone_trips[station["zone"]] += station["trips"]
zone_avg = {zone: round(sum(vals) / len(vals), 1) for zone, vals in zone_availability.items()}
zone_dock_avg = {zone: round(sum(vals) / len(vals), 1) for zone, vals in zone_dock.items()}
target = snapshot["zone_targets"]["availability_pct"]
shortage = sorted(zone_avg, key=lambda zone: target - zone_avg[zone], reverse=True)
theme_counts = Counter(row["theme"] for row in complaints)
zone_complaints = Counter(row["zone"] for row in complaints)
event_minutes = defaultdict(lambda: {"rebalance": 0, "outage": 0})
for row in events:
    event_minutes[row["zone"]]["rebalance"] += int(row["rebalance_minutes"])
    event_minutes[row["zone"]]["outage"] += int(row["outage_minutes"])


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def bar_chart(values: dict[str, float], title: str, suffix: str = "%") -> str:
    max_value = max(values.values()) or 1
    rows = []
    for label, value in values.items():
        width = max(8, round((value / max_value) * 100, 1))
        rows.append(
            f"<div class='bar-row'><span>{esc(label)}</span>"
            f"<b style='--w:{width}%;'>{esc(value)}{suffix}</b></div>"
        )
    return f"<div class='chart' data-chart='bar'><h3>{esc(title)}</h3>{''.join(rows)}</div>"


def weather_cards() -> str:
    cards = []
    for item in weather["events"]:
        zones = ", ".join(item["affected_zones"])
        cards.append(
            "<article class='weather-card'>"
            f"<h3>{esc(item['label'])}</h3>"
            f"<p>{esc(item['event_type'].title())} across {esc(zones)}</p>"
            f"<div class='impact'><span>{esc(item['trip_change_pct'])}% trips</span>"
            f"<span>{esc(item['availability_change_pct'])}% availability</span></div>"
            f"<small>{esc(item['ops_note'])}</small>"
            "</article>"
        )
    return "".join(cards)


def zone_matrix() -> str:
    rows = []
    priorities = {item["zone"]: item["priority"] for item in service_zones["zones"]}
    for zone in shortage:
        rows.append(
            "<tr>"
            f"<th>{esc(zone)}</th>"
            f"<td>{esc(zone_avg[zone])}%</td>"
            f"<td>{esc(zone_dock_avg[zone])}%</td>"
            f"<td>{zone_trips[zone]:,}</td>"
            f"<td>{esc(zone_complaints[zone])}</td>"
            f"<td>{esc(priorities[zone])}</td>"
            "</tr>"
        )
    return "<table class='matrix' data-chart='zone-matrix'><thead><tr><th>Zone</th><th>Avail.</th><th>Dock</th><th>Trips</th><th>Complaints</th><th>Priority</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


top_themes = theme_counts.most_common(4)
theme_values = {theme: count for theme, count in top_themes}
trip_delta = round((snapshot["quarter_totals"]["trips"] - snapshot["prior_quarter"]["trips"]) / snapshot["prior_quarter"]["trips"] * 100, 1)
uptime_delta = round(snapshot["quarter_totals"]["service_uptime_pct"] - snapshot["prior_quarter"]["service_uptime_pct"], 1)
availability_delta = round(snapshot["quarter_totals"]["avg_vehicle_availability_pct"] - snapshot["prior_quarter"]["avg_vehicle_availability_pct"], 1)

slides = [
    f"""
    <section class='slide title active' aria-current='true'>
      <div class='kicker'>{esc(snapshot['quarter'])} Operations Review</div>
      <h1>{esc(brand['brand'])} mobility network</h1>
      <p>{esc(snapshot['city'])} shared e-bike and scooter service, prepared for the Mobility Operations Council.</p>
      <ul><li>{snapshot['quarter_totals']['trips']:,} completed trips</li><li>{snapshot['fleet']['active_vehicles']:,} active vehicles</li><li>{snapshot['quarter_totals']['service_uptime_pct']}% service uptime</li></ul>
    </section>
    """,
    f"""
    <section class='slide summary'>
      <div class='kicker'>Executive summary</div>
      <h2>Trips rose while reliability signals softened</h2>
      <div class='metric-grid'>
        <article><b>+{trip_delta}%</b><span>trip growth quarter over quarter</span></article>
        <article><b>{uptime_delta}%</b><span>uptime movement vs prior quarter</span></article>
        <article><b>{availability_delta}%</b><span>availability movement vs prior quarter; satisfaction is {snapshot['quarter_totals']['customer_satisfaction_pct']}%</span></article>
      </div>
      <ul><li>Waterfront is the critical availability constraint.</li><li>North Campus shortage shows up in repeated morning complaints.</li><li>Weather events amplified rebalancing lag rather than reducing all demand.</li></ul>
    </section>
    """,
    f"""
    <section class='slide metrics'>
      <div class='kicker'>Key metrics</div>
      <h2>Demand is healthy; fleet readiness is the limiter</h2>
      <div class='metric-grid four'>
        <article><b>{snapshot['quarter_totals']['trips']:,}</b><span>trips</span></article>
        <article><b>${snapshot['quarter_totals']['revenue_usd']:,}</b><span>revenue</span></article>
        <article><b>{snapshot['fleet']['median_battery_pct']}%</b><span>median battery</span></article>
        <article><b>{snapshot['fleet']['maintenance_backlog']}</b><span>maintenance backlog</span></article>
      </div>
      {bar_chart(zone_avg, 'Average vehicle availability by zone')}
    </section>
    """,
    f"""
    <section class='slide zones'>
      <div class='kicker'>Zone comparison</div>
      <h2>Three zones sit below the {target}% availability target</h2>
      {zone_matrix()}
      <p class='callout'>{esc(shortage[0])} averages {zone_avg[shortage[0]]}% availability, so ferry arrivals can exhaust vehicles before rebalancing catches up.</p>
    </section>
    """,
    f"""
    <section class='slide weather'>
      <div class='kicker'>Weather impact</div>
      <h2>Weather pressure created operational asymmetry</h2>
      <div class='weather-grid'>{weather_cards()}</div>
      <p class='callout'>The March wind advisory increased Waterfront trips by {weather['events'][1]['trip_change_pct']}% while availability fell {weather['events'][1]['availability_change_pct']}%.</p>
    </section>
    """,
    f"""
    <section class='slide complaints'>
      <div class='kicker'>Customer complaints</div>
      <h2>Complaint themes match the shortage map</h2>
      {bar_chart(theme_values, 'Top complaint themes', '')}
      <ul><li>Morning vehicle shortage leads North Campus feedback.</li><li>Empty docks at ferry arrivals remains the most visible Waterfront issue.</li><li>Festival corral overflow and late-night scooter clutter are localized East Market risks.</li></ul>
    </section>
    """,
    f"""
    <section class='slide ops'>
      <div class='kicker'>Operating model</div>
      <h2>Rebalancing minutes show where intervention is needed</h2>
      {bar_chart({zone: event_minutes[zone]['rebalance'] for zone in shortage}, 'Quarter rebalancing minutes', 'm')}
      <ul><li>Waterfront uses the most rebalancing time but still misses availability.</li><li>North Campus needs a morning surge pattern, not evenly spread coverage.</li><li>Hilltop can donate capacity during weekday commute windows.</li></ul>
    </section>
    """,
    f"""
    <section class='slide roadmap'>
      <div class='kicker'>Next-quarter roadmap recommendations</div>
      <h2>Focus the plan on service recovery, not broad expansion</h2>
      <ol class='roadmap-list'>
        <li><b>Waterfront ferry pulse:</b> stage battery-ready vehicles before ferry arrivals and wind advisories.</li>
        <li><b>Campus morning surge:</b> schedule two targeted rebalance sweeps before class changes.</li>
        <li><b>Event corrals:</b> add temporary East Market parking capacity during festivals and night market hours.</li>
      </ol>
      <p class='callout'>Success target: lift Waterfront and North Campus above {target}% availability while holding complaints below {snapshot['zone_targets']['complaints_per_1000_trips']} per 1,000 trips.</p>
    </section>
    """,
    f"""
    <section class='slide closing'>
      <div class='kicker'>Council decision</div>
      <h2>Approve targeted operating changes for FY2026 Q2</h2>
      <ul><li>Protect the highest-demand commuter corridors first.</li><li>Link weather staffing to real demand response, not just expected trip loss.</li><li>Use complaint themes as an early warning signal for station-level shortages.</li></ul>
      <p>{esc(brand['brand'])} can grow trips and trust together if the next quarter fixes availability at the moments riders notice most.</p>
    </section>
    """,
]

html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(brand['brand'])} {esc(snapshot['quarter'])} Operations Review</title>
<style>
:root {{
  --harbor-blue: {colors['harbor_blue']};
  --signal-coral: {colors['signal_coral']};
  --tide-mint: {colors['tide_mint']};
  --sunlit-gold: {colors['sunlit_gold']};
  --ink: {colors['ink']};
  --mist: {colors['mist']};
  --white: {colors['white']};
  --heading: {brand['fonts']['heading']};
  --body: {brand['fonts']['body']};
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; width: 100%; height: 100%; overflow: hidden; background: var(--ink); color: var(--ink); font-family: var(--body); }}
main {{ position: fixed; inset: 0; overflow: hidden; }}
.slide {{ position: fixed; inset: 0; width: 100vw; height: 100vh; padding: 42px 54px 58px; display: grid; align-content: center; gap: 18px; background: var(--mist); opacity: 0; transform: translateX(6%); pointer-events: none; transition: opacity 420ms ease, transform 420ms ease; }}
.slide.active {{ opacity: 1; transform: translateX(0); pointer-events: auto; }}
.slide::after {{ content: ""; position: absolute; right: 0; top: 0; width: 28%; height: 100%; background: linear-gradient(180deg, rgba(66,194,168,.18), rgba(244,185,66,.20)); clip-path: polygon(26% 0,100% 0,100% 100%,0 100%); }}
.title, .closing {{ background: radial-gradient(circle at 20% 20%, rgba(66,194,168,.22), transparent 28%), var(--harbor-blue); color: var(--white); }}
.title::after, .closing::after {{ background: rgba(244,185,66,.22); }}
h1, h2, h3, p, ul, ol {{ margin: 0; position: relative; z-index: 1; }}
h1 {{ font-family: var(--heading); font-size: 58px; line-height: .98; max-width: 760px; }}
h2 {{ font-family: var(--heading); font-size: 38px; line-height: 1.05; max-width: 820px; }}
h3 {{ font-size: 16px; line-height: 1.2; }}
p, li, td, th, small {{ font-size: 16px; line-height: 1.35; }}
.kicker {{ position: relative; z-index: 1; color: var(--signal-coral); text-transform: uppercase; letter-spacing: .08em; font-weight: 800; font-size: 13px; }}
.title .kicker, .closing .kicker {{ color: var(--sunlit-gold); }}
.title p, .closing p {{ max-width: 720px; font-size: 20px; }}
ul, ol {{ display: grid; gap: 8px; padding-left: 22px; max-width: 850px; }}
.metric-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; position: relative; z-index: 1; }}
.metric-grid.four {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
.metric-grid article {{ border-left: 6px solid var(--tide-mint); background: var(--white); padding: 18px; min-height: 112px; box-shadow: 0 12px 28px rgba(23,32,38,.10); }}
.metric-grid b {{ display: block; font-size: 36px; color: var(--harbor-blue); line-height: 1; margin-bottom: 8px; }}
.chart {{ position: relative; z-index: 1; display: grid; gap: 8px; max-width: 920px; background: rgba(255,255,255,.84); padding: 16px; border: 1px solid rgba(11,79,108,.16); }}
.bar-row {{ display: grid; grid-template-columns: 190px 1fr; align-items: center; gap: 10px; }}
.bar-row span {{ font-size: 14px; font-weight: 700; }}
.bar-row b {{ display: block; width: var(--w); min-width: 52px; padding: 6px 8px; background: linear-gradient(90deg, var(--harbor-blue), var(--tide-mint)); color: var(--white); font-size: 13px; }}
.matrix {{ position: relative; z-index: 1; border-collapse: collapse; width: min(930px, 100%); background: var(--white); box-shadow: 0 12px 28px rgba(23,32,38,.10); }}
.matrix th, .matrix td {{ padding: 9px 10px; border-bottom: 1px solid rgba(11,79,108,.14); text-align: left; font-size: 14px; }}
.matrix th {{ color: var(--harbor-blue); }}
.weather-grid {{ position: relative; z-index: 1; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
.weather-card {{ background: var(--white); border-top: 6px solid var(--sunlit-gold); padding: 16px; display: grid; gap: 8px; min-height: 210px; box-shadow: 0 12px 28px rgba(23,32,38,.10); }}
.impact {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.impact span {{ background: var(--harbor-blue); color: var(--white); padding: 6px 8px; font-size: 13px; font-weight: 800; }}
.callout {{ position: relative; z-index: 1; max-width: 850px; padding: 14px 16px; background: rgba(244,91,105,.10); border-left: 6px solid var(--signal-coral); font-weight: 750; }}
.roadmap-list {{ list-style-position: inside; padding-left: 0; grid-template-columns: repeat(3, minmax(0, 1fr)); max-width: 980px; }}
.roadmap-list li {{ background: var(--white); padding: 16px; min-height: 150px; list-style: none; border-top: 6px solid var(--tide-mint); }}
.progress {{ position: fixed; z-index: 5; left: 24px; bottom: 20px; color: var(--white); background: rgba(23,32,38,.70); padding: 8px 12px; font-size: 13px; font-weight: 800; }}
.dots {{ position: fixed; z-index: 5; right: 24px; bottom: 24px; display: flex; gap: 6px; }}
.dots button {{ width: 10px; height: 10px; border-radius: 999px; border: 0; background: rgba(255,255,255,.45); padding: 0; }}
.dots button[aria-current='true'] {{ background: var(--sunlit-gold); width: 24px; }}
@media (max-width: 800px) {{
  .slide {{ padding: 24px 22px 50px; gap: 12px; }}
  h1 {{ font-size: 38px; }}
  h2 {{ font-size: 27px; }}
  p, li, td, th, small {{ font-size: 13px; line-height: 1.25; }}
  .title p, .closing p {{ font-size: 15px; }}
  .metric-grid, .metric-grid.four, .weather-grid, .roadmap-list {{ grid-template-columns: 1fr; gap: 8px; }}
  .metric-grid article {{ min-height: 72px; padding: 12px; }}
  .metric-grid b {{ font-size: 24px; }}
  .chart {{ padding: 10px; gap: 5px; }}
  .bar-row {{ grid-template-columns: 112px 1fr; gap: 6px; }}
  .bar-row span, .bar-row b {{ font-size: 11px; }}
  .matrix th, .matrix td {{ padding: 5px 4px; font-size: 10px; }}
  .weather-card {{ min-height: 0; padding: 11px; gap: 5px; }}
  .weather-card small {{ font-size: 11px; }}
  .roadmap-list li {{ min-height: 0; padding: 11px; }}
  .slide::after {{ width: 18%; opacity: .45; }}
}}
@media (max-height: 430px) {{
  .slide {{ padding: 14px 24px 34px; gap: 7px; }}
  h1 {{ font-size: 32px; }}
  h2 {{ font-size: 23px; }}
  h3 {{ font-size: 12px; }}
  p, li, td, th, small {{ font-size: 10px; line-height: 1.16; }}
  ul, ol {{ gap: 3px; }}
  .metric-grid, .metric-grid.four, .weather-grid, .roadmap-list {{ grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; }}
  .metric-grid article, .roadmap-list li, .weather-card {{ min-height: 0; padding: 8px; }}
  .metric-grid b {{ font-size: 20px; }}
  .chart {{ padding: 8px; gap: 3px; }}
  .bar-row {{ grid-template-columns: 110px 1fr; }}
  .bar-row span, .bar-row b {{ font-size: 9px; padding: 3px 5px; }}
  .matrix th, .matrix td {{ padding: 3px; font-size: 9px; }}
  .callout {{ padding: 7px 9px; }}
}}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ transition-duration: 1ms !important; animation-duration: 1ms !important; scroll-behavior: auto !important; }}
}}
</style>
</head>
<body>
<main aria-label="HarborLoop quarterly operations slide deck">
{''.join(slides)}
</main>
<div class="progress" aria-live="polite">Slide 1 / {len(slides)}</div>
<div class="dots" aria-label="Slide navigation"></div>
<script>
class PresentationController {{
  constructor() {{
    this.slides = [...document.querySelectorAll('.slide')];
    this.index = 0;
    this.progress = document.querySelector('.progress');
    this.dots = document.querySelector('.dots');
    this.touchX = 0;
    this.lastWheel = 0;
    this.buildDots();
    this.bind();
    this.show(0);
  }}
  buildDots() {{
    this.slides.forEach((_, i) => {{
      const button = document.createElement('button');
      button.type = 'button';
      button.setAttribute('aria-label', `Go to slide ${{i + 1}}`);
      button.addEventListener('click', () => this.show(i));
      this.dots.appendChild(button);
    }});
  }}
  bind() {{
    addEventListener('keydown', event => {{
      if (event.key === 'ArrowRight' || event.key === 'PageDown' || event.key === ' ') this.next();
      if (event.key === 'ArrowLeft' || event.key === 'PageUp') this.prev();
    }});
    addEventListener('wheel', event => {{
      event.preventDefault();
      const now = Date.now();
      if (now - this.lastWheel < 360) return;
      this.lastWheel = now;
      event.deltaY > 0 ? this.next() : this.prev();
    }}, {{ passive: false }});
    addEventListener('touchstart', event => {{ this.touchX = event.touches[0].clientX; }}, {{ passive: true }});
    addEventListener('touchend', event => {{
      const dx = event.changedTouches[0].clientX - this.touchX;
      if (Math.abs(dx) > 45) dx < 0 ? this.next() : this.prev();
    }}, {{ passive: true }});
  }}
  show(nextIndex) {{
    this.index = Math.max(0, Math.min(this.slides.length - 1, nextIndex));
    this.slides.forEach((slide, i) => {{
      const active = i === this.index;
      slide.classList.toggle('active', active);
      slide.setAttribute('aria-current', active ? 'true' : 'false');
      slide.setAttribute('aria-hidden', active ? 'false' : 'true');
    }});
    [...this.dots.children].forEach((dot, i) => dot.setAttribute('aria-current', i === this.index ? 'true' : 'false'));
    this.progress.textContent = `Slide ${{this.index + 1}} / ${{this.slides.length}}`;
  }}
  next() {{ this.show(this.index + 1); }}
  prev() {{ this.show(this.index - 1); }}
}}
new PresentationController();
</script>
</body>
</html>
"""

OUT.write_text(html_doc, encoding="utf-8")
PY
