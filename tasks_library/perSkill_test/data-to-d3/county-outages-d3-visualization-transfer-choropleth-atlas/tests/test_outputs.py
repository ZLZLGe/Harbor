import csv
import json
import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path("/root/output")
HTML_FILE = OUTPUT_DIR / "outage-atlas.html"
D3_FILE = OUTPUT_DIR / "js" / "d3.v6.min.js"
CSV_FILE = OUTPUT_DIR / "data" / "county_outages.csv"
GEOJSON_FILE = OUTPUT_DIR / "data" / "county_boundaries.geojson"


@pytest.fixture(scope="module")
def expected_data():
    with CSV_FILE.open(newline="") as handle:
        rows = list(csv.DictReader(handle))

    with GEOJSON_FILE.open() as handle:
        geojson = json.load(handle)

    return {"rows": rows, "geojson": geojson}


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

    server = ReusableTCPServer(("127.0.0.1", port), http.server.SimpleHTTPRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1560, "height": 1280})

        console_messages = []
        page_errors = []
        page.on("console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        page.goto(f"http://127.0.0.1:{port}/outage-atlas.html", wait_until="load", timeout=30000)
        page.wait_for_selector(".county-shape", timeout=15000)
        page.wait_for_selector(".bar-group", timeout=15000)
        page.wait_for_timeout(700)

        log_dir = Path("/logs/verifier")
        log_dir.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(log_dir / "outage-atlas.png"), full_page=True)

        page.console_messages = console_messages
        page.page_errors = page_errors

        yield page

        browser.close()

    server.shutdown()
    os.chdir(original_cwd)


def test_required_files_exist(expected_data):
    assert HTML_FILE.exists(), f"Expected HTML output at {HTML_FILE}"
    assert D3_FILE.exists(), f"Expected local D3 bundle at {D3_FILE}"
    assert CSV_FILE.exists(), f"Expected copied CSV data at {CSV_FILE}"
    assert GEOJSON_FILE.exists(), f"Expected copied GeoJSON data at {GEOJSON_FILE}"
    assert len(expected_data["rows"]) == 9, f"Expected 9 outage rows, found {len(expected_data['rows'])}."
    assert len(expected_data["geojson"]["features"]) == 9, f"Expected 9 county features, found {len(expected_data['geojson']['features'])}."


def test_page_renders_map_bars_and_legend(browser_page, expected_data):
    page = browser_page
    assert "County Outages" in page.title(), "The page title should describe the outage atlas."
    assert not page.page_errors, f"Unexpected page errors: {page.page_errors}"

    county_count = page.locator(".county-shape").count()
    bar_count = page.locator(".bar-group").count()
    legend_count = page.locator("#legend .legend-item").count()

    assert county_count == len(expected_data["rows"]), f"Expected {len(expected_data['rows'])} county shapes, found {county_count}."
    assert bar_count == len(expected_data["rows"]), f"Expected {len(expected_data['rows'])} ranked bars, found {bar_count}."
    assert legend_count == 5, f"Expected 5 severity legend entries, found {legend_count}."


def test_default_selection_is_highest_severity_county(browser_page):
    page = browser_page
    assert page.locator(".county-shape.selected").count() == 1, "Exactly one county should be selected by default."
    assert page.locator(".county-shape.selected").get_attribute("data-county") == "Douglas County", "The highest-severity county should be selected initially."
    assert page.locator(".bar-group.selected").get_attribute("data-county") == "Douglas County", "The top-ranked bar should be selected initially."
    assert page.locator("#detail-title").inner_text() == "Douglas County", "The detail panel should start on the highest-severity county."
    assert "8,150 customers out" in page.locator("#detail-customers").inner_text(), "The detail panel should show the selected county outage count."


def test_ranked_bars_are_sorted_descending(browser_page):
    page = browser_page
    ranked_counties = page.locator(".bar-group").evaluate_all("nodes => nodes.map(node => node.getAttribute('data-county'))")
    assert ranked_counties == [
        "Douglas County",
        "Harper County",
        "Ellis County",
        "Baker County",
        "Grant County",
        "Irwin County",
        "Clark County",
        "Adams County",
        "Franklin County",
    ], f"Bars should be ordered by descending severity index, found {ranked_counties}."


def test_hovering_a_county_updates_tooltip_and_details(browser_page):
    page = browser_page
    page.locator('.county-feature[data-county="Harper County"]').hover()
    tooltip_text = page.locator("#tooltip").inner_text(timeout=5000)

    assert "Harper County" in tooltip_text, "Tooltip should include the hovered county name."
    assert "Customers out: 7,520" in tooltip_text, "Tooltip should include the hovered county outage count."
    assert "Affected: 57.0%" in tooltip_text, "Tooltip should include the hovered county affected percentage."
    assert page.locator("#detail-title").inner_text() == "Harper County", "Hovering a county should update the detail panel."
    assert page.locator("#detail-facility").inner_text() == "Emergency Operations Center", "Hovering should surface the hovered county facility in the details panel."


def test_clicking_a_bar_syncs_the_map_selection(browser_page):
    page = browser_page
    page.locator('.bar-group[data-county="Grant County"]').click()
    page.wait_for_timeout(250)

    assert page.locator(".bar-group.selected").get_attribute("data-county") == "Grant County", "Clicking a bar should select that bar."
    assert page.locator('.county-shape.selected[data-county="Grant County"]').count() == 1, "Clicking a bar should highlight the matching county on the map."
    assert page.locator("#detail-title").inner_text() == "Grant County", "Clicking a bar should update the detail panel title."
    assert page.locator("#detail-severity").inner_text() == "55 / 100", "Clicking a bar should update the detail panel severity."


def test_clicking_a_county_syncs_the_bar_selection(browser_page):
    page = browser_page
    page.locator('.county-feature[data-county="Ellis County"]').click()
    page.wait_for_timeout(250)

    assert page.locator('.county-shape.selected[data-county="Ellis County"]').count() == 1, "Clicking a county should select that county."
    assert page.locator('.bar-group.selected[data-county="Ellis County"]').count() == 1, "Clicking a county should highlight the matching ranked bar."
    assert page.locator("#detail-title").inner_text() == "Ellis County", "Clicking a county should update the detail title."
    assert "Water Pumping Station" in page.locator("#detail-facility").inner_text(), "The detail panel should update to the clicked county facility."
