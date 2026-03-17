import csv
import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path("/root/output")
HTML_FILE = OUTPUT_DIR / "grant-clusters.html"
D3_FILE = OUTPUT_DIR / "js" / "d3.v6.min.js"
DATA_FILE = OUTPUT_DIR / "data" / "grants.csv"


@pytest.fixture(scope="module")
def expected_grants():
    with DATA_FILE.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows


@pytest.fixture(scope="module")
def browser_page():
    import http.server
    import socketserver
    import threading

    if not HTML_FILE.exists():
      pytest.fail(f"Missing primary output file: {HTML_FILE}")

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    port = 8765
    original_cwd = os.getcwd()
    os.chdir(OUTPUT_DIR)

    server = ReusableTCPServer(("", port), http.server.SimpleHTTPRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1560, "height": 1200})
        page.goto(f"http://127.0.0.1:{port}/grant-clusters.html", wait_until="load", timeout=30000)
        page.wait_for_selector("svg .node circle", timeout=15000)
        page.wait_for_selector("table tbody tr", timeout=15000)
        page.wait_for_timeout(1200)

        log_dir = Path("/logs/verifier")
        log_dir.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(log_dir / "grant-clusters.png"), full_page=True)

        yield page

        browser.close()

    server.shutdown()
    os.chdir(original_cwd)


def test_required_files_exist():
    assert HTML_FILE.exists(), f"Expected HTML output at {HTML_FILE}"
    assert D3_FILE.exists(), f"Expected local D3 bundle at {D3_FILE}"
    assert DATA_FILE.exists(), f"Expected copied dataset at {DATA_FILE}"


def test_page_renders_all_required_elements(browser_page, expected_grants):
    page = browser_page
    assert "University Grants" in page.title(), "The page title should describe the grants explorer."

    circle_count = page.locator("svg .node circle").count()
    row_count = page.locator("table tbody tr").count()
    legend_count = page.locator("#legend .legend-item").count()

    assert circle_count == len(expected_grants), f"Expected {len(expected_grants)} grant bubbles, found {circle_count}."
    assert row_count == len(expected_grants), f"Expected {len(expected_grants)} table rows, found {row_count}."
    assert legend_count == 5, f"Expected 5 sponsor type legend entries, found {legend_count}."

    first_row_text = page.locator("table tbody tr").first().inner_text()
    assert "GRT-105" in first_row_text, "The default table sort should place the largest award first."


def test_bubbles_are_labeled_and_use_multiple_colors(browser_page):
    page = browser_page
    labels = page.locator("svg .bubble-label")
    assert labels.count() == 18, "Each bubble should be labeled with its grant ID."
    assert labels.nth(0).inner_text().startswith("GRT-"), "Bubble labels should use grant IDs."

    fills = page.eval_on_selector_all(
        "svg .node circle",
        "els => Array.from(new Set(els.map(el => el.getAttribute('fill'))))"
    )
    assert len(fills) == 5, f"Expected 5 distinct sponsor colors, found {len(fills)}."


def test_tooltip_displays_grant_details(browser_page):
    page = browser_page
    node_data = page.eval_on_selector("svg .node circle", "el => el.__data__")
    page.locator("svg .node").first().hover()
    tooltip = page.locator("#tooltip")
    tooltip_text = tooltip.inner_text(timeout=5000)

    assert node_data["grant_id"] in tooltip_text, "Tooltip should include the hovered grant ID."
    assert node_data["university"] in tooltip_text, "Tooltip should include the university name."
    assert node_data["sponsor_type"] in tooltip_text, "Tooltip should include the sponsor type."


def test_table_headers_toggle_sorting(browser_page):
    page = browser_page
    award_header = page.locator("table thead th", has_text="Award Amount")

    first_row_before = page.locator("table tbody tr").first().inner_text()
    assert "GRT-105" in first_row_before, "Award Amount should default to descending order."

    award_header.click()
    page.wait_for_timeout(250)
    first_row_ascending = page.locator("table tbody tr").first().inner_text()
    assert "GRT-115" in first_row_ascending, "Clicking Award Amount once should switch to ascending order."

    award_header.click()
    page.wait_for_timeout(250)
    first_row_descending = page.locator("table tbody tr").first().inner_text()
    assert "GRT-105" in first_row_descending, "Clicking Award Amount again should restore descending order."


def test_clicking_a_bubble_highlights_the_matching_row(browser_page):
    page = browser_page
    target_grant = "GRT-113"
    target_row = page.locator("table tbody tr", has_text=target_grant).first()

    row_background_before = target_row.evaluate("el => getComputedStyle(el).backgroundColor")
    page.locator("svg .node", has_text=target_grant).click()
    page.wait_for_timeout(250)
    row_background_after = target_row.evaluate("el => getComputedStyle(el).backgroundColor")

    assert row_background_before != row_background_after, "Clicking a bubble should visibly highlight the matching table row."


def test_clicking_a_row_changes_the_matching_bubble_style(browser_page):
    page = browser_page
    target_grant = "GRT-111"
    row = page.locator("table tbody tr", has_text=target_grant).first()

    circle_info_before = page.eval_on_selector_all(
        "svg .node",
        f"""nodes => {{
            const target = nodes.find(node => node.textContent.includes("{target_grant}"));
            const circle = target.querySelector("circle");
            return {{
                className: target.getAttribute("class") || "",
                strokeWidth: getComputedStyle(circle).strokeWidth,
                filter: getComputedStyle(circle).filter
            }};
        }}"""
    )

    row.click()
    page.wait_for_timeout(250)

    circle_info_after = page.eval_on_selector_all(
        "svg .node",
        f"""nodes => {{
            const target = nodes.find(node => node.textContent.includes("{target_grant}"));
            const circle = target.querySelector("circle");
            return {{
                className: target.getAttribute("class") || "",
                strokeWidth: getComputedStyle(circle).strokeWidth,
                filter: getComputedStyle(circle).filter
            }};
        }}"""
    )

    assert circle_info_before != circle_info_after, "Clicking a row should visibly highlight the matching bubble."


def test_same_color_bubbles_form_compact_clusters(browser_page):
    page = browser_page
    cluster_stats = page.eval_on_selector_all(
        "svg .node circle",
        """circles => {
            const groups = {};
            circles.forEach(circle => {
                const bbox = circle.getBoundingClientRect();
                const fill = circle.getAttribute('fill');
                const center = { x: bbox.left + bbox.width / 2, y: bbox.top + bbox.height / 2 };
                groups[fill] = groups[fill] || [];
                groups[fill].push(center);
            });

            return Object.values(groups).map(points => {
                const centroid = points.reduce((acc, point) => ({
                    x: acc.x + point.x / points.length,
                    y: acc.y + point.y / points.length
                }), { x: 0, y: 0 });
                const avgDistance = points.reduce((sum, point) => {
                    return sum + Math.hypot(point.x - centroid.x, point.y - centroid.y);
                }, 0) / points.length;
                return { size: points.length, avgDistance };
            });
        }"""
    )

    assert len(cluster_stats) == 5, "Expected cluster stats for each sponsor color."
    for cluster in cluster_stats:
        assert cluster["avgDistance"] < 155, f"Same-color bubbles should cluster together; found average spread {cluster['avgDistance']:.2f}."
