from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
from playwright.sync_api import sync_playwright


APP = Flask(__name__)

TASK_ROOT = Path(__import__("os").environ.get("TASK_ROOT", "/app"))
WORKSPACE_ROOT = TASK_ROOT / "workspace"
OUTPUT_ROOT = TASK_ROOT / "output"
DECK_HTML_PATH = OUTPUT_ROOT / "deck" / "index.html"
SUBMISSION_PATH = OUTPUT_ROOT / "deck_submission.json"
TRACE_PATH = Path("/tmp/launch_deck_qa_trace.jsonl")
LAST_VALIDATE_PATH = Path("/tmp/launch_deck_last_validate.json")
WEEKLY_KPI_PATH = WORKSPACE_ROOT / "data" / "weekly_kpis.csv"
FEATURE_MATRIX_PATH = WORKSPACE_ROOT / "data" / "feature_matrix.csv"
QUOTE_PATH = WORKSPACE_ROOT / "data" / "customer_quotes.json"
JOURNEY_PATH = WORKSPACE_ROOT / "data" / "user_journey.json"

REQUIRED_ROLES = [
    "cover",
    "kpi-overview",
    "comparison",
    "evidence",
    "journey-diagram",
    "risks-next-steps",
]
VIEWPORTS = [
    {"name": "primary", "width": 1440, "height": 900},
    {"name": "secondary", "width": 1280, "height": 720},
]
ALLOWED_SOURCE_PREFIXES = (
    "/app/workspace/brief/",
    "/app/workspace/specs/",
    "/app/workspace/data/",
    "/app/workspace/mirror/site/",
)
CHROMIUM_EXECUTABLE_PATH = Path(__import__("os").environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/usr/bin/chromium"))
BROWSER_PROBE = """
() => {
  const slides = Array.from(document.querySelectorAll('[data-slide-role][data-slide-index]'));
  const activeSlides = slides.filter((slide) => slide.classList.contains('active'));
  const dots = Array.from(document.querySelectorAll('[data-active-slide-indicator] span, .indicator span'));
  const activeDots = dots
    .map((dot, index) => dot.classList.contains('active') ? index : -1)
    .filter((index) => index >= 0);
  const activeSlide = activeSlides[0] ?? null;
  const describe = (element) => {
    if (!element) return 'unknown';
    const parts = [element.tagName.toLowerCase()];
    const slideRole = element.getAttribute('data-slide-role');
    const slideIndex = element.getAttribute('data-slide-index');
    if (slideRole) parts.push(`[role="${slideRole}"]`);
    if (slideIndex) parts.push(`[index="${slideIndex}"]`);
    if (element.id) parts.push(`#${element.id}`);
    const className = String(element.className || '').trim();
    if (className) parts.push(`.${className.replace(/\\s+/g, '.')}`);
    return parts.join('');
  };

  const result = {
    activeCount: activeSlides.length,
    activeRole: activeSlide ? activeSlide.getAttribute('data-slide-role') || '' : '',
    activeIndex: activeSlide ? Number(activeSlide.getAttribute('data-slide-index')) : -1,
    activeDotCount: activeDots.length,
    activeDotIndex: activeDots.length === 1 ? activeDots[0] : -1,
    navButtonsVisible: false,
    titleVisible: false,
    scrollOverflow: false,
    widthOverflow: false,
    offenders: [],
  };

  const prev = document.querySelector('[data-nav-prev]');
  const next = document.querySelector('[data-nav-next]');
  if (prev && next) {
    const prevRect = prev.getBoundingClientRect();
    const nextRect = next.getBoundingClientRect();
    result.navButtonsVisible = (
      prevRect.width > 0 &&
      prevRect.height > 0 &&
      nextRect.width > 0 &&
      nextRect.height > 0 &&
      prevRect.bottom <= window.innerHeight + 1 &&
      nextRect.bottom <= window.innerHeight + 1
    );
  }

  if (!activeSlide) {
    return result;
  }

  const title = activeSlide.querySelector('h1, h2, h3');
  if (title) {
    const titleRect = title.getBoundingClientRect();
    result.titleVisible = titleRect.width > 0 && titleRect.height > 0;
  }

  result.scrollOverflow = (
    activeSlide.scrollHeight > activeSlide.clientHeight + 1 ||
    activeSlide.scrollWidth > activeSlide.clientWidth + 1
  );
  result.widthOverflow = activeSlide.scrollWidth > activeSlide.clientWidth + 1;

  const slideRect = activeSlide.getBoundingClientRect();
  const nodes = Array.from(activeSlide.querySelectorAll('*'));
  for (const node of nodes) {
    const style = window.getComputedStyle(node);
    if (style.display === 'none' || style.visibility === 'hidden' || style.position === 'fixed') {
      continue;
    }
    const rect = node.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) {
      continue;
    }
    const outside = (
      rect.left < slideRect.left - 1 ||
      rect.right > slideRect.right + 1 ||
      rect.top < slideRect.top - 1 ||
      rect.bottom > slideRect.bottom + 1
    );
    if (outside) {
      result.offenders.push(describe(node));
      if (result.offenders.length >= 5) {
        break;
      }
    }
  }

  return result;
}
"""


def resolve_task_path(path_str: str) -> Path:
    if path_str.startswith("/app/"):
        return TASK_ROOT / path_str.removeprefix("/app/")
    if path_str == "/app":
        return TASK_ROOT
    return Path(path_str)


def trace(event: dict[str, Any]) -> None:
    TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    enriched = {
        "ts": datetime.now(timezone.utc).isoformat(),
        **event,
    }
    with TRACE_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(enriched, ensure_ascii=True, sort_keys=True) + "\n")


def canonical_json_sha(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compact_failures(failures: list[str], label: str) -> list[str]:
    return [label] if failures else []


def visible_text(element: Any) -> str:
    return " ".join(element.stripped_strings)


def collect_external_urls(html: str) -> list[str]:
    urls = re.findall(r"""(?:(?:src|href)=["']([^"']+)["']|url\(([^)]+)\))""", html, flags=re.IGNORECASE)
    found: list[str] = []
    for left, right in urls:
        candidate = (left or right).strip().strip("'\"")
        if candidate.lower().startswith(("http://", "https://", "//")):
            found.append(candidate)
    return found


def load_html_soup() -> BeautifulSoup:
    if not DECK_HTML_PATH.exists():
        raise FileNotFoundError(DECK_HTML_PATH)
    return BeautifulSoup(DECK_HTML_PATH.read_text(encoding="utf-8"), "html.parser")


def load_weekly_kpis() -> list[dict[str, str]]:
    with WEEKLY_KPI_PATH.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_feature_matrix() -> list[dict[str, str]]:
    with FEATURE_MATRIX_PATH.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_quotes() -> list[dict[str, Any]]:
    return json.loads(QUOTE_PATH.read_text(encoding="utf-8"))


def load_journey() -> dict[str, Any]:
    return json.loads(JOURNEY_PATH.read_text(encoding="utf-8"))


def validate_slide_dom(soup: BeautifulSoup) -> tuple[int, list[str], list[str]]:
    slides = soup.select("[data-slide-role][data-slide-index]")
    overflow_failures: list[str] = []
    navigation_failures: list[str] = []

    if len(slides) != 6:
        overflow_failures.append(f"expected 6 slides, found {len(slides)}")
        return len(slides), overflow_failures, navigation_failures

    roles = [slide.get("data-slide-role", "").strip() for slide in slides]
    if roles != REQUIRED_ROLES:
        navigation_failures.append(f"role order mismatch: {roles}")

    for expected_index, slide in enumerate(slides):
        index_attr = slide.get("data-slide-index", "").strip()
        if index_attr != str(expected_index):
            navigation_failures.append(f"slide index mismatch at position {expected_index}: {index_attr!r}")
        if not visible_text(slide):
            overflow_failures.append(f"slide {expected_index} is visually empty")
        title = slide.find(["h1", "h2", "h3"])
        if title is None or not visible_text(title):
            navigation_failures.append(f"slide {expected_index} missing visible title")
        if slide.get("data-needs-scroll", "").lower() == "true":
            overflow_failures.append(f"slide {expected_index} declares scroll-dependent content")

    if soup.select("[data-active-slide-indicator]") == []:
        navigation_failures.append("missing active slide indicator")

    if not soup.find(attrs={"data-nav-next": True}) or not soup.find(attrs={"data-nav-prev": True}):
        navigation_failures.append("missing previous/next navigation controls")

    return len(slides), overflow_failures, navigation_failures


def validate_browser_contract() -> list[str]:
    failures: list[str] = []

    def check_viewport(page: Any, viewport: dict[str, Any]) -> None:
        width = int(viewport["width"])
        height = int(viewport["height"])
        label = str(viewport["name"])

        page.set_viewport_size({"width": width, "height": height})
        page.goto(DECK_HTML_PATH.resolve().as_uri(), wait_until="load")
        page.wait_for_timeout(200)

        state = page.evaluate(BROWSER_PROBE)
        if state["activeCount"] != 1 or state["activeIndex"] != 0:
            failures.append(f"{label}: initial active slide is invalid")
        if state["activeDotCount"] != 1 or state["activeDotIndex"] != 0:
            failures.append(f"{label}: initial active indicator is invalid")
        if not state["navButtonsVisible"]:
            failures.append(f"{label}: navigation buttons are not fully visible")

        for expected_index, expected_role in enumerate(REQUIRED_ROLES):
            if expected_index == 0:
                current = state
            else:
                page.keyboard.press("ArrowRight")
                page.wait_for_timeout(120)
                current = page.evaluate(BROWSER_PROBE)

            if current["activeCount"] != 1:
                failures.append(f"{label}: expected exactly one active slide at {expected_index}")
            if current["activeIndex"] != expected_index or current["activeRole"] != expected_role:
                failures.append(
                    f"{label}: active slide mismatch at {expected_index} "
                    f"(got index={current['activeIndex']} role={current['activeRole']!r})"
                )
            if current["activeDotCount"] != 1 or current["activeDotIndex"] != expected_index:
                failures.append(f"{label}: indicator mismatch at slide {expected_index}")
            if not current["titleVisible"]:
                failures.append(f"{label}: slide {expected_index} title is not visible")
            if current["scrollOverflow"] or current["widthOverflow"]:
                failures.append(f"{label}: slide {expected_index} overflows its viewport")
            if current["offenders"]:
                failures.append(
                    f"{label}: slide {expected_index} has out-of-bounds elements "
                    + ", ".join(current["offenders"])
                )

        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(100)
        after_last = page.evaluate(BROWSER_PROBE)
        if after_last["activeIndex"] != len(REQUIRED_ROLES) - 1:
            failures.append(f"{label}: ArrowRight should clamp at the last slide")

        page.click("[data-nav-prev]")
        page.wait_for_timeout(100)
        previous = page.evaluate(BROWSER_PROBE)
        if previous["activeIndex"] != len(REQUIRED_ROLES) - 2:
            failures.append(f"{label}: Previous button did not navigate backward")

        page.click("[data-nav-next]")
        page.wait_for_timeout(100)
        recovered = page.evaluate(BROWSER_PROBE)
        if recovered["activeIndex"] != len(REQUIRED_ROLES) - 1:
            failures.append(f"{label}: Next button did not navigate forward")

    launch_kwargs: dict[str, Any] = {
        "headless": True,
        "args": ["--no-sandbox", "--disable-dev-shm-usage"],
    }
    if CHROMIUM_EXECUTABLE_PATH.exists():
        launch_kwargs["executable_path"] = str(CHROMIUM_EXECUTABLE_PATH)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**launch_kwargs)
        try:
            page = browser.new_page()
            for viewport in VIEWPORTS:
                check_viewport(page, viewport)
        finally:
            browser.close()

    return failures


def validate_source_refs(payload: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    slides = payload.get("slides")
    if not isinstance(slides, list) or len(slides) != 6:
        return ["submission slide manifest is missing or incomplete"]

    kpi_ref_found = False
    journey_ref_found = False

    for expected_index, expected_role in enumerate(REQUIRED_ROLES):
        slide = slides[expected_index]
        if slide.get("index") != expected_index:
            failures.append(f"slide {expected_index} has incorrect index")
        if slide.get("role") != expected_role:
            failures.append(f"slide {expected_index} has incorrect role")
        title = str(slide.get("title", "")).strip()
        if not title:
            failures.append(f"slide {expected_index} missing title")

        source_refs = slide.get("source_refs")
        if not isinstance(source_refs, list) or not source_refs:
            failures.append(f"slide {expected_index} missing source_refs")
            continue

        for ref in source_refs:
            if not isinstance(ref, str) or not ref.startswith(ALLOWED_SOURCE_PREFIXES):
                failures.append(f"slide {expected_index} has invalid source ref {ref!r}")
                continue
            if not resolve_task_path(ref).exists():
                failures.append(f"slide {expected_index} references missing source path {ref}")
            if expected_role == "kpi-overview" and ref == "/app/workspace/data/weekly_kpis.csv":
                kpi_ref_found = True
            if expected_role == "journey-diagram" and ref == "/app/workspace/data/user_journey.json":
                journey_ref_found = True

    if not kpi_ref_found:
        failures.append("kpi-overview slide does not reference weekly_kpis.csv")
    if not journey_ref_found:
        failures.append("journey-diagram slide does not reference user_journey.json")
    return failures


def validate_visual_components(soup: BeautifulSoup) -> list[str]:
    failures: list[str] = []
    kpi_slide = soup.select_one('[data-slide-role="kpi-overview"]')
    journey_slide = soup.select_one('[data-slide-role="journey-diagram"]')

    if kpi_slide is None:
        failures.append("missing kpi-overview slide")
    else:
        has_chart = bool(
            kpi_slide.find("svg")
            or kpi_slide.find("canvas")
            or kpi_slide.select("[data-chart-bar], [data-chart-point], .chart-bar, .chart-point")
        )
        if not has_chart:
            failures.append("kpi-overview slide is missing a structured chart")

    if journey_slide is None:
        failures.append("missing journey-diagram slide")
    else:
        has_diagram = bool(
            journey_slide.find("svg")
            or journey_slide.find("canvas")
            or journey_slide.select("[data-journey-node], [data-journey-edge], .journey-node, .journey-edge")
        )
        if not has_diagram:
            failures.append("journey-diagram slide is missing a structured diagram")

    return failures


def validate_kpi_fidelity(soup: BeautifulSoup) -> list[str]:
    failures: list[str] = []
    kpi_slide = soup.select_one('[data-slide-role="kpi-overview"]')
    if kpi_slide is None:
        return ["missing kpi-overview slide"]

    expected_rows = load_weekly_kpis()
    expected_chart = {
        (row["week_start"], "median_approval_hours", row["median_approval_hours"])
        for row in expected_rows
    }
    observed_chart = {
        (
            node.get("data-chart-week", "").strip(),
            node.get("data-chart-metric", "").strip(),
            node.get("data-chart-value", "").strip(),
        )
        for node in kpi_slide.select("[data-chart-week][data-chart-metric][data-chart-value]")
    }
    missing_chart = sorted(expected_chart - observed_chart)
    if missing_chart:
        failures.append(
            "missing KPI chart marks for "
            + ", ".join(f"{week}:{metric}={value}" for week, metric, value in missing_chart[:4])
        )

    latest_row = expected_rows[-1]
    expected_metrics = {
        "median_approval_hours": latest_row["median_approval_hours"],
        "on_time_launch_rate": latest_row["on_time_launch_rate"],
        "stakeholder_adoption_rate": latest_row["stakeholder_adoption_rate"],
    }
    observed_metrics = {
        node.get("data-kpi-metric", "").strip(): node.get("data-kpi-latest", "").strip()
        for node in kpi_slide.select("[data-kpi-metric][data-kpi-latest]")
    }
    for metric, value in expected_metrics.items():
        if observed_metrics.get(metric) != value:
            failures.append(f"missing or incorrect KPI summary for {metric}")

    if not kpi_slide.select('[data-source-ref="/app/workspace/data/weekly_kpis.csv"]'):
        failures.append("kpi-overview slide is missing DOM-level weekly_kpis.csv trace markers")

    return failures


def validate_comparison_fidelity(soup: BeautifulSoup) -> list[str]:
    failures: list[str] = []
    comparison_slide = soup.select_one('[data-slide-role="comparison"]')
    if comparison_slide is None:
        return ["missing comparison slide"]

    expected_rows = load_feature_matrix()
    expected = {
        row["capability"]: {
            "atlasflow_review": row["atlasflow_review"],
            "notion": row["notion"],
            "airtable": row["airtable"],
            "monday_work_management": row["monday_work_management"],
        }
        for row in expected_rows
    }
    observed: dict[str, dict[str, str]] = {}
    for row in comparison_slide.select(
        "[data-capability][data-atlasflow_review][data-notion][data-airtable][data-monday_work_management]"
    ):
        capability = row.get("data-capability", "").strip()
        observed[capability] = {
            "atlasflow_review": row.get("data-atlasflow_review", "").strip(),
            "notion": row.get("data-notion", "").strip(),
            "airtable": row.get("data-airtable", "").strip(),
            "monday_work_management": row.get("data-monday_work_management", "").strip(),
        }

    for capability, statuses in expected.items():
        if capability not in observed:
            failures.append(f"comparison slide missing capability row {capability!r}")
            continue
        if observed[capability] != statuses:
            failures.append(f"comparison slide status mismatch for capability {capability!r}")

    if not comparison_slide.select('[data-source-ref="/app/workspace/data/feature_matrix.csv"]'):
        failures.append("comparison slide is missing DOM-level feature_matrix.csv trace markers")

    return failures


def validate_quote_fidelity(soup: BeautifulSoup) -> list[str]:
    failures: list[str] = []
    quotes = {quote["quote_id"]: quote for quote in load_quotes()}
    required_by_role = {
        "cover": {"q3"},
        "evidence": {"q1", "q2"},
        "journey-diagram": {"q5"},
        "risks-next-steps": {"q4"},
    }

    for role, expected_ids in required_by_role.items():
        slide = soup.select_one(f'[data-slide-role="{role}"]')
        if slide is None:
            failures.append(f"missing {role} slide for quote validation")
            continue
        observed_ids = {
            node.get("data-quote-id", "").strip()
            for node in slide.select("[data-quote-id]")
            if node.get("data-quote-id", "").strip()
        }
        missing_ids = sorted(expected_ids - observed_ids)
        if missing_ids:
            failures.append(f"{role} slide is missing required quote ids: {', '.join(missing_ids)}")
        for quote_id in observed_ids:
            if quote_id not in quotes:
                failures.append(f"{role} slide references unknown quote id {quote_id!r}")
        if observed_ids and not slide.select('[data-source-ref="/app/workspace/data/customer_quotes.json"]'):
            failures.append(f"{role} slide is missing customer_quotes.json trace markers")

    return failures


def validate_journey_fidelity(soup: BeautifulSoup) -> list[str]:
    failures: list[str] = []
    journey_slide = soup.select_one('[data-slide-role="journey-diagram"]')
    if journey_slide is None:
        return ["missing journey-diagram slide"]

    journey = load_journey()
    expected_nodes = {node["id"] for node in journey["nodes"]}
    observed_nodes = {
        node.get("data-journey-node-id", "").strip()
        for node in journey_slide.select("[data-journey-node-id]")
        if node.get("data-journey-node-id", "").strip()
    }
    missing_nodes = sorted(expected_nodes - observed_nodes)
    if missing_nodes:
        failures.append("journey diagram missing nodes: " + ", ".join(missing_nodes))

    expected_edges = {(edge["from"], edge["to"]) for edge in journey["edges"]}
    observed_edges = {
        (
            edge.get("data-journey-edge-from", "").strip(),
            edge.get("data-journey-edge-to", "").strip(),
        )
        for edge in journey_slide.select("[data-journey-edge-from][data-journey-edge-to]")
    }
    missing_edges = sorted(expected_edges - observed_edges)
    if missing_edges:
        failures.append(
            "journey diagram missing edges: "
            + ", ".join(f"{left}->{right}" for left, right in missing_edges[:5])
        )

    if not journey_slide.select('[data-source-ref="/app/workspace/data/user_journey.json"]'):
        failures.append("journey-diagram slide is missing DOM-level user_journey.json trace markers")

    return failures


def validate_story_boundaries(soup: BeautifulSoup) -> list[str]:
    failures: list[str] = []
    risks_slide = soup.select_one('[data-slide-role="risks-next-steps"]')
    if risks_slide is None:
        return ["missing risks-next-steps slide"]

    risks_text = visible_text(risks_slide).lower()
    if "external agency review" not in risks_text and "separate system" not in risks_text:
        failures.append("risks-next-steps slide does not acknowledge the external agency review boundary")
    if "replacement" not in risks_text and "project management" not in risks_text:
        failures.append("risks-next-steps slide does not acknowledge the work-management boundary")
    return failures


def validate_html_against_submission(payload: dict[str, Any], soup: BeautifulSoup) -> list[str]:
    failures: list[str] = []
    slides = soup.select("[data-slide-role][data-slide-index]")
    declared = payload.get("slides", [])

    if len(slides) != len(declared):
        failures.append("submission slide manifest count does not match HTML")
        return failures

    for slide_dom, slide_meta in zip(slides, declared):
        if slide_dom.get("data-slide-role", "").strip() != slide_meta.get("role", ""):
            failures.append(f"role mismatch for slide {slide_meta.get('index')}")
        title = slide_dom.find(["h1", "h2", "h3"])
        dom_title = visible_text(title) if title else ""
        if dom_title.strip() != str(slide_meta.get("title", "")).strip():
            failures.append(f"title mismatch for slide {slide_meta.get('index')}")

    return failures


@APP.get("/manifest")
def manifest() -> Any:
    payload = {
        "manifest_id": "atlasflow-review-deck-contract-v1",
        "viewport_contract": VIEWPORTS,
        "required_roles": REQUIRED_ROLES,
        "requires_keyboard_navigation": True,
        "requires_browser_cleanliness": True,
        "requires_offline_assets": True,
        "submission_fields": ["job_id", "entry_html", "slide_count", "submitted_at", "slides"],
    }
    trace({"event": "manifest", "manifest_id": payload["manifest_id"]})
    return jsonify(payload)


@APP.post("/validate")
def validate() -> Any:
    payload = request.get_json(force=True, silent=False)
    soup = load_html_soup()
    html_text = DECK_HTML_PATH.read_text(encoding="utf-8")

    rendered_slide_count, overflow_failures, navigation_failures = validate_slide_dom(soup)
    browser_contract_failures = validate_browser_contract()
    source_trace_failures = validate_source_refs(payload)
    visual_component_failures = validate_visual_components(soup)
    kpi_data_failures = validate_kpi_fidelity(soup)
    comparison_failures = validate_comparison_fidelity(soup)
    quote_failures = validate_quote_fidelity(soup)
    journey_data_failures = validate_journey_fidelity(soup)
    boundary_failures = validate_story_boundaries(soup)
    manifest_alignment_failures = validate_html_against_submission(payload, soup)
    external_dependency_failures = collect_external_urls(html_text)

    navigation_failures.extend(manifest_alignment_failures)

    accepted = not any(
        [
            overflow_failures,
            browser_contract_failures,
            source_trace_failures,
            navigation_failures,
            external_dependency_failures,
            visual_component_failures,
            kpi_data_failures,
            comparison_failures,
            quote_failures,
            journey_data_failures,
            boundary_failures,
        ]
    )

    receipt = {
        "accepted": accepted,
        "job_id": payload.get("job_id"),
        "rendered_slide_count": rendered_slide_count,
        "overflow_failures": compact_failures(overflow_failures, "overflow contract mismatch"),
        "browser_contract_failures": compact_failures(browser_contract_failures, "browser contract mismatch"),
        "source_trace_failures": compact_failures(source_trace_failures, "source trace mismatch"),
        "navigation_failures": compact_failures(navigation_failures, "navigation contract mismatch"),
        "external_dependency_failures": compact_failures(
            external_dependency_failures,
            "external dependency detected",
        ),
        "visual_component_failures": compact_failures(
            visual_component_failures,
            "visual component contract mismatch",
        ),
        "kpi_data_failures": compact_failures(kpi_data_failures, "kpi fidelity mismatch"),
        "comparison_failures": compact_failures(comparison_failures, "comparison fidelity mismatch"),
        "quote_failures": compact_failures(quote_failures, "quote fidelity mismatch"),
        "journey_data_failures": compact_failures(journey_data_failures, "journey fidelity mismatch"),
        "boundary_failures": compact_failures(boundary_failures, "story boundary mismatch"),
    }

    payload_sha = canonical_json_sha(payload)
    summary = {
        "job_id": payload.get("job_id"),
        "payload_sha256": payload_sha,
        "accepted": accepted,
        "rendered_slide_count": rendered_slide_count,
    }
    LAST_VALIDATE_PATH.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    trace(
        {
            "event": "validate",
            "job_id": payload.get("job_id"),
            "payload_sha256": payload_sha,
            "accepted": accepted,
        }
    )
    return jsonify(receipt)

def main() -> None:
    APP.run(host="0.0.0.0", port=8364)


if __name__ == "__main__":
    main()
