import csv
import http.server
import os
import socketserver
import threading
from collections import defaultdict
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

ROOT_DIR = Path(os.environ.get("TASK_ROOT", "/root"))
OUTPUT_DIR = ROOT_DIR / "output"
DATA_DIR = ROOT_DIR / "data"
HTML_PATH = OUTPUT_DIR / "bus-reliability.html"
ASSET_DIR = OUTPUT_DIR / "assets"
ROUTE_CSV = DATA_DIR / "route_performance.csv"
STOP_CSV = DATA_DIR / "stop_delays.csv"


def load_route_rows():
    with ROUTE_CSV.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["scheduled_trips"] = int(row["scheduled_trips"])
        row["on_time_trips"] = int(row["on_time_trips"])
        row["late_trips"] = row["scheduled_trips"] - row["on_time_trips"]
        row["on_time_rate"] = row["on_time_trips"] / row["scheduled_trips"]
    return rows


def load_stop_rows():
    with STOP_CSV.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["total_arrivals"] = int(row["total_arrivals"])
        row["late_arrivals"] = int(row["late_arrivals"])
        row["delays_over_10_min"] = int(row["delays_over_10_min"])
    return rows


ROUTE_ROWS = load_route_rows()
STOP_ROWS = load_stop_rows()
TIME_BINS = sorted({row["time_bin"] for row in ROUTE_ROWS})


def rate_text(value):
    return f"{value * 100:.1f}%"


def integer_text(value):
    return f"{value:,}"


def route_summaries():
    grouped = defaultdict(list)
    for row in ROUTE_ROWS:
        grouped[row["route_id"]].append(row)

    summaries = []
    for route_id, rows in grouped.items():
        rows.sort(key=lambda row: row["time_bin"])
        scheduled = sum(row["scheduled_trips"] for row in rows)
        on_time = sum(row["on_time_trips"] for row in rows)
        summaries.append({
            "route_id": route_id,
            "route_name": rows[0]["route_name"],
            "scheduled_trips": scheduled,
            "on_time_trips": on_time,
            "late_trips": scheduled - on_time,
            "all_day_rate": on_time / scheduled,
            "points": rows,
        })
    summaries.sort(key=lambda row: (row["all_day_rate"], row["route_id"]))
    return summaries


ROUTES = route_summaries()
ROUTES_BY_ID = {row["route_id"]: row for row in ROUTES}
DEFAULT_ROUTE = ROUTES[0]


def aggregate_stops(route_id, time_bin=None):
    grouped = defaultdict(lambda: {
        "stop_id": "",
        "stop_name": "",
        "late_arrivals": 0,
        "delays_over_10_min": 0,
        "total_arrivals": 0,
    })
    for row in STOP_ROWS:
        if row["route_id"] != route_id:
            continue
        if time_bin is not None and row["time_bin"] != time_bin:
            continue
        entry = grouped[row["stop_id"]]
        entry["stop_id"] = row["stop_id"]
        entry["stop_name"] = row["stop_name"]
        entry["late_arrivals"] += row["late_arrivals"]
        entry["delays_over_10_min"] += row["delays_over_10_min"]
        entry["total_arrivals"] += row["total_arrivals"]
    rows = list(grouped.values())
    rows.sort(key=lambda row: (-row["delays_over_10_min"], -row["late_arrivals"], row["stop_id"]))
    return rows


@pytest.fixture(scope="module")
def page():
    if not HTML_PATH.exists():
        pytest.fail(f"Missing expected HTML output: {HTML_PATH}")

    original_cwd = os.getcwd()
    os.chdir(OUTPUT_DIR)

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            return

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    httpd = ReusableTCPServer(("127.0.0.1", 0), QuietHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1500, "height": 1200})
        page_errors = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.goto(f"http://127.0.0.1:{port}/bus-reliability.html", wait_until="networkidle", timeout=30000)
        page.wait_for_selector("g.route-panel", timeout=10000)
        page.wait_for_timeout(300)
        page.page_errors = page_errors
        yield page
        browser.close()

    httpd.shutdown()
    os.chdir(original_cwd)


def test_output_files_exist():
    expected_paths = [
        HTML_PATH,
        ASSET_DIR / "d3.v7.min.js",
        ASSET_DIR / "app.js",
        ASSET_DIR / "styles.css",
        ASSET_DIR / "route_performance.csv",
        ASSET_DIR / "stop_delays.csv",
    ]
    for path in expected_paths:
        assert path.exists(), f"Missing required output file: {path}"


def test_page_loads_and_sections_exist(page):
    assert not page.page_errors, f"Page had runtime errors: {page.page_errors}"
    assert page.evaluate("typeof d3 !== 'undefined'"), "D3 must be available on the page"
    assert page.locator("h1").count() == 1
    assert page.locator("h1").inner_text().strip()
    assert page.locator(".subtitle").count() == 1
    assert page.locator(".subtitle").inner_text().strip()
    assert page.locator("#route-selector .route-chip").count() == len(ROUTES)
    assert page.locator("g.route-panel").count() == len(ROUTES)
    assert page.locator("path.reliability-line").count() == len(ROUTES)
    assert page.locator("circle.time-point").count() == len(ROUTES) * len(TIME_BINS)
    assert page.locator("rect.focus-band").count() == len(ROUTES) * len(TIME_BINS)
    assert page.locator("#stop-detail-table").count() == 1


def test_route_selector_and_panel_order_follow_all_day_rate(page):
    expected_ids = [row["route_id"] for row in ROUTES]
    chip_ids = page.locator("#route-selector .route-chip").evaluate_all(
        "(nodes) => nodes.map((node) => node.getAttribute('data-route-id'))"
    )
    panel_ids = page.locator("g.route-panel").evaluate_all(
        "(nodes) => nodes.map((node) => node.getAttribute('data-route-id'))"
    )
    assert chip_ids == expected_ids
    assert panel_ids == expected_ids

    selected_chip = page.locator('#route-selector .route-chip[aria-pressed=\"true\"]')
    assert selected_chip.count() == 1
    assert selected_chip.get_attribute("data-route-id") == DEFAULT_ROUTE["route_id"]

    selected_panel = page.locator('g.route-panel[data-selected=\"true\"]')
    assert selected_panel.count() == 1
    assert selected_panel.get_attribute("data-route-id") == DEFAULT_ROUTE["route_id"]


def test_time_points_expose_required_data_attributes(page):
    point = page.locator('circle.time-point[data-route-id="R21"][data-time-bin="16:00"]')
    assert point.count() == 1
    assert point.get_attribute("data-on-time-rate") == "0.5000"
    assert point.get_attribute("data-late-trips") == "4"


def test_default_summary_and_table_use_selected_route_all_day_scope(page):
    focus_text = page.locator("#focus-readout").inner_text()
    assert DEFAULT_ROUTE["route_name"] in focus_text
    assert "All day" in focus_text

    summary_text = page.locator("#interval-summary").inner_text()
    assert "All day" in summary_text
    assert rate_text(DEFAULT_ROUTE["all_day_rate"]) in summary_text
    assert integer_text(DEFAULT_ROUTE["late_trips"]) in summary_text
    assert integer_text(DEFAULT_ROUTE["scheduled_trips"]) in summary_text

    expected_rows = aggregate_stops(DEFAULT_ROUTE["route_id"])[:5]
    rows = page.locator("#stop-detail-table tbody tr")
    assert rows.count() == len(expected_rows)
    first_row = rows.first
    assert first_row.get_attribute("data-route-id") == DEFAULT_ROUTE["route_id"]
    assert first_row.get_attribute("data-stop-id") == expected_rows[0]["stop_id"]
    assert first_row.get_attribute("data-scope") == "all-day"
    first_cells = first_row.locator("td")
    assert first_cells.nth(0).inner_text() == expected_rows[0]["stop_name"]
    assert first_cells.nth(1).inner_text() == integer_text(expected_rows[0]["late_arrivals"])
    assert first_cells.nth(2).inner_text() == integer_text(expected_rows[0]["delays_over_10_min"])
    assert first_cells.nth(3).inner_text() == integer_text(expected_rows[0]["total_arrivals"])
    assert first_cells.nth(4).inner_text() == rate_text(expected_rows[0]["late_arrivals"] / expected_rows[0]["total_arrivals"])


def test_hovering_selected_focus_band_updates_summary_and_table(page):
    band = page.locator('rect.focus-band[data-route-id="R21"][data-time-bin="16:00"]')
    band.hover()
    page.wait_for_timeout(120)

    current_band = page.locator('rect.focus-band[aria-current="true"]')
    assert current_band.count() == 1
    assert current_band.get_attribute("data-route-id") == "R21"
    assert current_band.get_attribute("data-time-bin") == "16:00"

    focus_text = page.locator("#focus-readout").inner_text()
    assert "Route 21 Crosstown" in focus_text
    assert "16:00" in focus_text

    summary_text = page.locator("#interval-summary").inner_text()
    assert "16:00" in summary_text
    assert "50.0%" in summary_text
    assert "4" in summary_text
    assert "8" in summary_text

    expected_rows = aggregate_stops("R21", "16:00")[:5]
    rows = page.locator("#stop-detail-table tbody tr")
    assert rows.first.get_attribute("data-scope") == "16:00"
    actual_stop_ids = rows.evaluate_all("(nodes) => nodes.map((node) => node.getAttribute('data-stop-id'))")
    assert actual_stop_ids == [row["stop_id"] for row in expected_rows]


def test_mouse_leaving_selected_panel_restores_all_day_scope(page):
    page.locator("h1").hover()
    page.wait_for_timeout(120)

    assert page.locator('rect.focus-band[aria-current="true"]').count() == 0
    focus_text = page.locator("#focus-readout").inner_text()
    assert DEFAULT_ROUTE["route_name"] in focus_text
    assert "All day" in focus_text

    first_row = page.locator("#stop-detail-table tbody tr").first
    assert first_row.get_attribute("data-scope") == "all-day"
    assert first_row.get_attribute("data-stop-id") == aggregate_stops(DEFAULT_ROUTE["route_id"])[0]["stop_id"]


def test_clicking_route_chip_changes_selected_route_and_table(page):
    page.locator('#route-selector .route-chip[data-route-id="R8"]').click()
    page.wait_for_timeout(120)

    selected_chip = page.locator('#route-selector .route-chip[aria-pressed="true"]')
    assert selected_chip.count() == 1
    assert selected_chip.get_attribute("data-route-id") == "R8"

    selected_panel = page.locator('g.route-panel[data-selected="true"]')
    assert selected_panel.count() == 1
    assert selected_panel.get_attribute("data-route-id") == "R8"
    assert page.locator('rect.focus-band[aria-current="true"]').count() == 0

    summary_text = page.locator("#interval-summary").inner_text()
    assert "All day" in summary_text
    assert rate_text(ROUTES_BY_ID["R8"]["all_day_rate"]) in summary_text
    assert integer_text(ROUTES_BY_ID["R8"]["late_trips"]) in summary_text
    assert integer_text(ROUTES_BY_ID["R8"]["scheduled_trips"]) in summary_text

    expected_rows = aggregate_stops("R8")[:5]
    rows = page.locator("#stop-detail-table tbody tr")
    assert rows.first.get_attribute("data-route-id") == "R8"
    assert rows.first.get_attribute("data-scope") == "all-day"
    actual_stop_ids = rows.evaluate_all("(nodes) => nodes.map((node) => node.getAttribute('data-stop-id'))")
    assert actual_stop_ids == [row["stop_id"] for row in expected_rows]
