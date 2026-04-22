#!/usr/bin/env python3
from __future__ import annotations

import csv
import html
import json
import os
from pathlib import Path


TASK_ROOT = Path(os.environ.get("TASK_ROOT", "/app"))
WORKSPACE_ROOT = TASK_ROOT / "workspace"
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", str(TASK_ROOT / "output")))
DECK_HTML_PATH = OUTPUT_ROOT / "deck" / "index.html"


def read_brief() -> str:
    return (WORKSPACE_ROOT / "brief" / "creative_brief.md").read_text(encoding="utf-8")


def read_kpis() -> list[dict[str, str]]:
    with (WORKSPACE_ROOT / "data" / "weekly_kpis.csv").open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_feature_matrix() -> list[dict[str, str]]:
    with (WORKSPACE_ROOT / "data" / "feature_matrix.csv").open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_quotes() -> list[dict[str, str]]:
    return json.loads((WORKSPACE_ROOT / "data" / "customer_quotes.json").read_text(encoding="utf-8"))


def read_journey() -> dict[str, object]:
    return json.loads((WORKSPACE_ROOT / "data" / "user_journey.json").read_text(encoding="utf-8"))


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def format_pct(value: float) -> str:
    return f"{round(value * 100)}%"


def build_chart_rows(kpis: list[dict[str, str]]) -> str:
    max_hours = max(int(row["median_approval_hours"]) for row in kpis)
    blocks: list[str] = []
    for row in kpis:
        hours = int(row["median_approval_hours"])
        height_pct = max(18, round(hours / max_hours * 100))
        label = row["week_start"][5:].replace("-", "/")
        blocks.append(
            f"""            <div class="chart-bar" data-source-ref="/app/workspace/data/weekly_kpis.csv">
              <span data-chart-bar data-chart-week="{esc(row["week_start"])}" data-chart-metric="median_approval_hours" data-chart-value="{hours}" style="height: {height_pct}%"></span>
              <label>{esc(label)}</label>
            </div>"""
        )
    return "\n".join(blocks)


def build_comparison_rows(rows: list[dict[str, str]]) -> str:
    status_keys = [
        ("atlasflow_review", "AtlasFlow"),
        ("notion", "Notion"),
        ("airtable", "Airtable"),
        ("monday_work_management", "Monday"),
    ]
    chunks: list[str] = []
    for row in rows:
        cells = [f"<td>{esc(row['capability'])}</td>"]
        for key, _label in status_keys:
            status = row[key]
            cls = esc(status)
            cells.append(f'<td class="{cls}">{esc(status.title())}</td>')
        chunks.append(
            f"""                <tr data-capability="{esc(row["capability"])}" data-source-ref="/app/workspace/data/feature_matrix.csv">
{''.join(cells)}
                </tr>"""
        )
    return "\n".join(chunks)


def quote_map(quotes: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {quote["quote_id"]: quote for quote in quotes}


def render_quote_card(quote: dict[str, str], extra_class: str = "quote-card") -> str:
    return (
        f'<article class="{extra_class}" data-quote-id="{esc(quote["quote_id"])}" '
        f'data-source-ref="/app/workspace/data/customer_quotes.json">'
        f"<p>{esc(quote['quote_text'])}</p>"
        f"<strong>{esc(quote['speaker_name'])}, {esc(quote['speaker_role'])}</strong>"
        f"</article>"
    )


def build_journey_svg(journey: dict[str, object]) -> str:
    node_positions = {
        "intake": (40, 55, 160, 90, "#ffffff", 22),
        "triage": (240, 55, 160, 90, "#ffffff", 22),
        "creative_review": (440, 55, 160, 90, "#ffffff", 22),
        "brand_review": (600, 55, 160, 90, "#ffffff", 20),
        "regional_review": (760, 55, 160, 90, "#ffffff", 20),
        "exec_summary": (820, 180, 150, 90, "#d8e7f5", 22),
        "signoff": (610, 300, 170, 90, "#ffffff", 22),
        "rework": (240, 280, 180, 90, "#fff3ee", 22),
    }
    edge_paths = {
        ("intake", "triage"): "M120 100 L280 100",
        ("triage", "creative_review"): "M360 100 L440 100",
        ("creative_review", "brand_review"): "M520 100 L600 100",
        ("brand_review", "regional_review"): "M680 100 L760 100",
        ("regional_review", "exec_summary"): "M840 100 L900 200",
        ("exec_summary", "signoff"): "M900 270 L760 340",
        ("creative_review", "rework"): "M520 145 L380 300",
        ("brand_review", "rework"): "M680 145 L410 320",
        ("regional_review", "rework"): "M840 145 L430 335",
        ("rework", "creative_review"): "M360 280 L500 145",
    }

    nodes = journey["nodes"]  # type: ignore[index]
    edges = journey["edges"]  # type: ignore[index]

    edge_chunks: list[str] = []
    for edge in edges:
        start = edge["from"]  # type: ignore[index]
        end = edge["to"]  # type: ignore[index]
        stroke = "#ff6b3d" if end != "rework" and start != "rework" else "#8c9bad"
        edge_chunks.append(
            f'            <path data-journey-edge data-journey-edge-from="{esc(start)}" '
            f'data-journey-edge-to="{esc(end)}" data-source-ref="/app/workspace/data/user_journey.json" '
            f'd="{edge_paths[(start, end)]}" stroke="{stroke}" stroke-width="4" fill="none" '
            'marker-end="url(#arrow)"></path>'
        )

    node_chunks: list[str] = []
    for node in nodes:
        node_id = node["id"]  # type: ignore[index]
        x, y, width, height, fill, font_size = node_positions[node_id]
        center_x = x + width / 2
        text_y = y + height / 2 - 5
        node_chunks.append(
            f"""            <g data-journey-node data-journey-node-id="{esc(node_id)}" data-source-ref="/app/workspace/data/user_journey.json">
              <rect x="{x}" y="{y}" width="{width}" height="{height}" rx="18" fill="{fill}"></rect>
              <text x="{center_x}" y="{text_y}" text-anchor="middle" font-size="{font_size}" fill="#132235">{esc(node["label"])}</text>
            </g>"""
        )

    return "\n".join(edge_chunks + node_chunks)


def build_html() -> str:
    _brief = read_brief()
    kpis = read_kpis()
    matrix = read_feature_matrix()
    quotes = quote_map(read_quotes())
    journey = read_journey()

    first_row = kpis[0]
    latest_row = kpis[-1]
    cover_quote = quotes["q3"]
    journey_quote = quotes["q5"]
    risk_quote = quotes["q4"]

    chart_rows = build_chart_rows(kpis)
    comparison_rows = build_comparison_rows(matrix)
    evidence_cards = "\n".join(
        f"          {render_quote_card(quotes[qid])}" for qid in ["q1", "q2", "q3", "q4"]
    )
    journey_svg = build_journey_svg(journey)

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>AtlasFlow Review Launch Storyboard</title>
    <style>
      :root {{
        --ink: #132235;
        --accent: #ff6b3d;
        --mist: #eef3f7;
        --sky: #d8e7f5;
        --paper: #fcfbf8;
        --muted: #5f6f81;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: Georgia, "Times New Roman", serif;
        background: linear-gradient(180deg, #f6f7f9 0%, #e7edf3 100%);
        color: var(--ink);
        overflow: hidden;
      }}
      .deck {{
        height: 100vh;
        width: 100vw;
        position: relative;
      }}
      .slide {{
        display: none;
        height: 100vh;
        padding: 36px 42px 84px;
        overflow: hidden;
      }}
      .slide.active {{ display: grid; }}
      .slide-grid {{ grid-template-rows: auto auto 1fr auto; gap: 14px; }}
      .kicker {{
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.18em;
        color: var(--accent);
      }}
      h1, h2, h3 {{
        margin: 0;
        line-height: 1.04;
      }}
      h1 {{ font-size: clamp(2.4rem, 3.8vw, 4rem); max-width: 1100px; }}
      h2 {{ font-size: clamp(1.8rem, 2.8vw, 2.9rem); max-width: 1100px; }}
      h3 {{ font-size: 1.1rem; }}
      p, li, th, td {{
        font-size: 0.92rem;
        line-height: 1.4;
      }}
      .lede {{
        max-width: 760px;
        font-size: 1rem;
      }}
      .source-chip {{
        display: inline-block;
        padding: 7px 11px;
        border-radius: 999px;
        background: rgba(19, 34, 53, 0.08);
        color: var(--muted);
        font-size: 0.76rem;
        margin-right: 8px;
        margin-top: 6px;
      }}
      .hero-grid,
      .comparison-grid,
      .evidence-grid,
      .risk-grid,
      .journey-wrap,
      .metric-row {{
        display: grid;
        gap: 14px;
      }}
      .hero-grid {{ grid-template-columns: 1.45fr 1fr; align-items: start; }}
      .comparison-grid {{ grid-template-columns: 1.18fr 0.82fr; }}
      .evidence-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .journey-wrap {{ grid-template-columns: 1.16fr 0.84fr; align-items: start; }}
      .risk-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
      .panel,
      .quote-card,
      .risk-card,
      .metric-card {{
        background: rgba(255, 255, 255, 0.9);
        border-radius: 20px;
        padding: 16px;
        box-shadow: 0 18px 32px rgba(19, 34, 53, 0.08);
      }}
      .metric-row {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
      .metric-card strong {{
        display: block;
        margin-top: 6px;
        font-size: 1.4rem;
      }}
      .chart {{
        display: grid;
        grid-template-columns: repeat(9, minmax(0, 1fr));
        align-items: end;
        gap: 8px;
        height: 200px;
        padding: 8px 0 6px;
      }}
      .chart-bar {{
        display: grid;
        align-items: end;
        gap: 8px;
      }}
      .chart-bar span {{
        display: block;
        width: 100%;
        border-radius: 12px 12px 0 0;
        background: linear-gradient(180deg, #ff835b 0%, #ff6b3d 100%);
      }}
      .chart-bar label {{
        text-align: center;
        color: var(--muted);
        font-size: 0.72rem;
      }}
      table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.82rem;
      }}
      th, td {{
        padding: 7px 6px;
        border-bottom: 1px solid rgba(19, 34, 53, 0.1);
        text-align: left;
      }}
      .yes {{ color: #0d6c49; font-weight: 700; }}
      .partial {{ color: #8d5d00; font-weight: 700; }}
      .no {{ color: #b22a1f; font-weight: 700; }}
      svg {{
        width: 100%;
        height: 338px;
        background: rgba(255, 255, 255, 0.9);
        border-radius: 20px;
        box-shadow: 0 18px 32px rgba(19, 34, 53, 0.08);
      }}
      .journey-note {{
        background: rgba(216, 231, 245, 0.8);
        border-radius: 16px;
        padding: 14px;
        margin-bottom: 12px;
      }}
      .footer {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 18px;
      }}
      .indicator {{
        position: absolute;
        left: 24px;
        bottom: 20px;
        display: flex;
        gap: 8px;
      }}
      .indicator span {{
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: rgba(19, 34, 53, 0.18);
      }}
      .indicator span.active {{ background: var(--accent); }}
      .nav {{
        position: absolute;
        right: 24px;
        bottom: 20px;
        display: flex;
        gap: 10px;
      }}
      .nav button {{
        border: none;
        border-radius: 999px;
        padding: 8px 14px;
        background: var(--ink);
        color: #fff;
        cursor: pointer;
      }}
      @media (min-width: 1360px) and (min-height: 860px) {{
        .slide {{
          padding: 44px 52px 88px;
        }}
        .slide-grid {{
          gap: 18px;
        }}
        h1 {{ font-size: clamp(2.8rem, 4vw, 4.3rem); }}
        h2 {{ font-size: clamp(2rem, 3vw, 3.1rem); }}
        p, li, th, td {{ font-size: 0.98rem; }}
        .chart {{ height: 250px; gap: 10px; }}
        .metric-card strong {{ font-size: 1.7rem; }}
        svg {{ height: 420px; }}
      }}
    </style>
  </head>
  <body>
    <main class="deck">
      <section class="slide slide-grid active" data-slide-index="0" data-slide-role="cover">
        <div class="kicker">AtlasFlow Review launch storyboard</div>
        <h1>AtlasFlow Review gives launch teams one visible approval path.</h1>
        <div class="hero-grid">
          <div class="panel">
            <p class="lede">
              The launch story is strongest when framed as operational clarity, not generic productivity.
              Over the latest review window, approval hours, late changes, and review cycles all move in the
              right direction while launch reliability and stakeholder adoption improve together.
            </p>
            <ul>
              <li>Active workspaces rise from {esc(first_row["active_workspaces"])} to {esc(latest_row["active_workspaces"])} during the latest nine-week window.</li>
              <li>Median approval time falls from {esc(first_row["median_approval_hours"])} hours to {esc(latest_row["median_approval_hours"])} hours as on-time launch rate reaches {format_pct(float(latest_row["on_time_launch_rate"]))}.</li>
              <li>The product story is most credible when we frame AtlasFlow Review as the structured review layer for launch-heavy teams.</li>
            </ul>
          </div>
          <aside class="panel">
            <h3>Leadership takeaway</h3>
            <p>
              Launch now with an operations-forward story: AtlasFlow Review is strongest when review routing,
              sign-off ownership, and launch readiness all need to stay visible in one place.
            </p>
            <p data-quote-id="q3" data-source-ref="/app/workspace/data/customer_quotes.json">{esc(cover_quote["quote_text"])}</p>
          </aside>
        </div>
        <div class="footer">
          <div>
            <span class="source-chip" data-source-ref="/app/workspace/brief/creative_brief.md">Source: creative_brief.md</span>
            <span class="source-chip" data-source-ref="/app/workspace/data/customer_quotes.json">Source: customer_quotes.json</span>
            <span class="source-chip" data-source-ref="/app/workspace/mirror/site/index.html">Source: mirror/site/index.html</span>
          </div>
        </div>
      </section>

      <section class="slide slide-grid" data-slide-index="1" data-slide-role="kpi-overview">
        <div class="kicker">Readiness signals</div>
        <h2>Readiness signals point to faster, steadier launch review.</h2>
        <div class="metric-row">
          <div class="metric-card" data-kpi-metric="median_approval_hours" data-kpi-latest="{esc(latest_row["median_approval_hours"])}" data-source-ref="/app/workspace/data/weekly_kpis.csv">
            <div class="kicker">Median approval</div>
            <strong>{esc(latest_row["median_approval_hours"])}h</strong>
            <p>Down from {esc(first_row["median_approval_hours"])}h over the observed window.</p>
          </div>
          <div class="metric-card" data-kpi-metric="on_time_launch_rate" data-kpi-latest="{esc(latest_row["on_time_launch_rate"])}" data-source-ref="/app/workspace/data/weekly_kpis.csv">
            <div class="kicker">On-time launch rate</div>
            <strong>{format_pct(float(latest_row["on_time_launch_rate"]))}</strong>
            <p>Improves as review cycles tighten and blockers surface earlier.</p>
          </div>
          <div class="metric-card" data-kpi-metric="stakeholder_adoption_rate" data-kpi-latest="{esc(latest_row["stakeholder_adoption_rate"])}" data-source-ref="/app/workspace/data/weekly_kpis.csv">
            <div class="kicker">Stakeholder adoption</div>
            <strong>{format_pct(float(latest_row["stakeholder_adoption_rate"]))}</strong>
            <p>Cross-functional usage is now broad enough to support a launch narrative.</p>
          </div>
        </div>
        <div class="panel">
          <div class="chart" aria-label="Approval hours by week">
{chart_rows}
          </div>
          <p class="lede">
            The launch signal is not just adoption growth. It is the simultaneous drop in approval hours,
            review cycles, and late changes while launch reliability improves.
          </p>
        </div>
        <div class="footer">
          <div>
            <span class="source-chip" data-source-ref="/app/workspace/data/weekly_kpis.csv">Source: weekly_kpis.csv</span>
            <span class="source-chip" data-source-ref="/app/workspace/brief/creative_brief.md">Source: creative_brief.md</span>
          </div>
        </div>
      </section>

      <section class="slide slide-grid" data-slide-index="2" data-slide-role="comparison">
        <div class="kicker">Capability position</div>
        <h2>AtlasFlow Review is strongest where review routing and sign-off need structure.</h2>
        <div class="comparison-grid">
          <div class="panel">
            <table>
              <thead>
                <tr><th>Capability</th><th>AtlasFlow</th><th>Notion</th><th>Airtable</th><th>Monday</th></tr>
              </thead>
              <tbody>
{comparison_rows}
              </tbody>
            </table>
          </div>
          <div class="panel">
            <h3>How to frame the comparison</h3>
            <ul>
              <li>Do not position AtlasFlow Review as a universal work-management replacement.</li>
              <li>Position it as the most structured option when launches require sequenced review, accountable sign-off, and executive readiness visibility.</li>
              <li>Keep adjacent planning or tracking workflows in familiar tools where the matrix shows only partial overlap.</li>
            </ul>
          </div>
        </div>
        <div class="footer">
          <div>
            <span class="source-chip" data-source-ref="/app/workspace/data/feature_matrix.csv">Source: feature_matrix.csv</span>
            <span class="source-chip" data-source-ref="/app/workspace/brief/creative_brief.md">Source: creative_brief.md</span>
          </div>
        </div>
      </section>

      <section class="slide slide-grid" data-slide-index="3" data-slide-role="evidence">
        <div class="kicker">Customer evidence</div>
        <h2>Customer evidence is strongest on visibility, accountability, and launch readiness.</h2>
        <div class="evidence-grid">
{evidence_cards}
        </div>
        <div class="footer">
          <div>
            <span class="source-chip" data-source-ref="/app/workspace/data/customer_quotes.json">Source: customer_quotes.json</span>
            <span class="source-chip" data-source-ref="/app/workspace/brief/creative_brief.md">Source: creative_brief.md</span>
          </div>
        </div>
      </section>

      <section class="slide slide-grid" data-slide-index="4" data-slide-role="journey-diagram">
        <div class="kicker">Intended workflow</div>
        <h2>The intended workflow moves from intake to sign-off with explicit rework loops.</h2>
        <div class="journey-wrap">
          <svg viewBox="0 0 1000 430" aria-label="Campaign review flow">
            <defs>
              <marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto">
                <path d="M0,0 L12,6 L0,12 z" fill="#ff6b3d"></path>
              </marker>
            </defs>
{journey_svg}
          </svg>
          <div class="panel">
            <div class="journey-note">
              AtlasFlow Review is most persuasive when the workflow stays staged and accountable:
              intake, triage, review, regional confirmation, executive summary, and sign-off, with a visible rework loop.
            </div>
            {render_quote_card(journey_quote)}
            <ul>
              <li>Operations owns triage and deadline integrity.</li>
              <li>Creative, brand, and regional handoffs become visible instead of implicit.</li>
              <li>Leadership sees blockers before the final sign-off moment.</li>
            </ul>
          </div>
        </div>
        <div class="footer">
          <div>
            <span class="source-chip" data-source-ref="/app/workspace/data/user_journey.json">Source: user_journey.json</span>
            <span class="source-chip" data-source-ref="/app/workspace/brief/creative_brief.md">Source: creative_brief.md</span>
          </div>
        </div>
      </section>

      <section class="slide slide-grid" data-slide-index="5" data-slide-role="risks-next-steps">
        <div class="kicker">Risks and next steps</div>
        <h2>Launch confidence is real, but external review and multilingual workflows remain out of scope.</h2>
        <div class="risk-grid">
          <article class="risk-card">
            <h3>Risk</h3>
            <p>External agency review still sits outside the strongest product workflow and should not be overclaimed in launch messaging.</p>
          </article>
          <article class="risk-card">
            <h3>Boundary</h3>
            <p>The story is grounded in structured launch review and executive readiness visibility. It is not a replacement for every project management workflow.</p>
          </article>
          <article class="risk-card">
            <h3>Next step</h3>
            <p>Use the launch window to validate whether regional teams need deeper localized review support before broadening the scope narrative.</p>
          </article>
        </div>
        <div class="panel" data-quote-id="q4" data-source-ref="/app/workspace/data/customer_quotes.json">
          <p>{esc(risk_quote["quote_text"])}</p>
          <strong>{esc(risk_quote["speaker_name"])}, {esc(risk_quote["speaker_role"])}</strong>
        </div>
        <div class="footer">
          <div>
            <span class="source-chip" data-source-ref="/app/workspace/brief/creative_brief.md">Source: creative_brief.md</span>
            <span class="source-chip" data-source-ref="/app/workspace/data/customer_quotes.json">Source: customer_quotes.json</span>
            <span class="source-chip" data-source-ref="/app/workspace/specs/deck_contract.md">Source: deck_contract.md</span>
          </div>
        </div>
      </section>

      <div class="indicator" data-active-slide-indicator aria-label="slide progress">
        <span class="active"></span><span></span><span></span><span></span><span></span><span></span>
      </div>
      <nav class="nav">
        <button type="button" data-nav-prev>Previous</button>
        <button type="button" data-nav-next>Next</button>
      </nav>
    </main>
    <script>
      (() => {{
        const slides = Array.from(document.querySelectorAll(".slide"));
        const dots = Array.from(document.querySelectorAll(".indicator span"));
        const prev = document.querySelector("[data-nav-prev]");
        const next = document.querySelector("[data-nav-next]");
        let active = 0;

        function render() {{
          slides.forEach((slide, index) => {{
            slide.classList.toggle("active", index === active);
            slide.setAttribute("aria-hidden", index === active ? "false" : "true");
          }});
          dots.forEach((dot, index) => {{
            dot.classList.toggle("active", index === active);
            dot.setAttribute("aria-current", index === active ? "true" : "false");
          }});
        }}

        function setActive(index) {{
          active = Math.max(0, Math.min(slides.length - 1, index));
          render();
        }}

        prev.addEventListener("click", () => setActive(active - 1));
        next.addEventListener("click", () => setActive(active + 1));
        window.addEventListener("keydown", (event) => {{
          if (event.key === "ArrowRight") setActive(active + 1);
          if (event.key === "ArrowLeft") setActive(active - 1);
        }});

        render();
      }})();
    </script>
  </body>
</html>
"""


def main() -> None:
    DECK_HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
    DECK_HTML_PATH.write_text(build_html(), encoding="utf-8")
    print(f"Wrote {DECK_HTML_PATH}")


if __name__ == "__main__":
    main()
