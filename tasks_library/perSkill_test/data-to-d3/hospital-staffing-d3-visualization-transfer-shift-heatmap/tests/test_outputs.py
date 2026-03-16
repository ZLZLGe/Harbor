import csv
import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path("/root/output")
HTML_FILE = OUTPUT_DIR / "staffing-heatmap.html"
D3_FILE = OUTPUT_DIR / "js" / "d3.v6.min.js"
HEATMAP_FILE = OUTPUT_DIR / "data" / "staffing_heatmap.csv"
TREND_FILE = OUTPUT_DIR / "data" / "unit_hourly_gaps.csv"


@pytest.fixture(scope="module")
def expected_data():
    with HEATMAP_FILE.open(newline="") as handle:
        heatmap_rows = list(csv.DictReader(handle))

    with TREND_FILE.open(newline="") as handle:
        trend_rows = list(csv.DictReader(handle))

    return {
        "heatmap": heatmap_rows,
        "trend": trend_rows,
    }


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
        page = browser.new_page(viewport={"width": 1540, "height": 1180})

        console_messages = []
        page_errors = []
        page.on("console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        page.goto(f"http://127.0.0.1:{port}/staffing-heatmap.html", wait_until="load", timeout=30000)
        page.wait_for_selector(".heatmap-cell", timeout=15000)
        page.wait_for_selector(".trend-line", timeout=15000)
        page.wait_for_timeout(1000)

        log_dir = Path("/logs/verifier")
        log_dir.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(log_dir / "staffing-heatmap.png"), full_page=True)

        page.console_messages = console_messages
        page.page_errors = page_errors

        yield page

        browser.close()

    server.shutdown()
    os.chdir(original_cwd)


def test_required_files_exist():
    assert HTML_FILE.exists(), f"Expected HTML output at {HTML_FILE}"
    assert D3_FILE.exists(), f"Expected local D3 bundle at {D3_FILE}"
    assert HEATMAP_FILE.exists(), f"Expected copied heatmap CSV at {HEATMAP_FILE}"
    assert TREND_FILE.exists(), f"Expected copied trend CSV at {TREND_FILE}"


def test_page_renders_heatmap_and_legends(browser_page, expected_data):
    page = browser_page
    assert "Hospital Staffing" in page.title(), "The page title should describe the staffing dashboard."
    assert not page.page_errors, f"Unexpected page errors: {page.page_errors}"

    heatmap_cell_count = page.locator(".heatmap-cell").count()
    weekday_label_count = page.locator(".weekday-label").count()
    shift_label_count = page.locator("#heatmap .tick-label").all_inner_texts().count("Night")

    assert heatmap_cell_count == len(expected_data["heatmap"]), f"Expected {len(expected_data['heatmap'])} heatmap cells, found {heatmap_cell_count}."
    assert weekday_label_count == 7, f"Expected 7 weekday labels, found {weekday_label_count}."
    assert page.locator("#heat-legend .legend-item").count() == 5, "Expected five heat legend stops."
    assert page.locator("#unit-legend .legend-item").count() == 4, "Expected four unit legend entries."
    assert shift_label_count == 1, "Expected the heatmap axis to include the Night shift label."


def test_default_selection_is_monday_day_shift(browser_page):
    page = browser_page
    assert page.locator(".heatmap-cell.selected").count() == 1, "One heatmap cell should be selected by default."
    assert page.locator(".heatmap-cell.selected").get_attribute("data-weekday") == "Monday", "The default selection should start on Monday."
    assert page.locator(".heatmap-cell.selected").get_attribute("data-shift") == "Day", "The default selection should start on the Day shift."
    assert "Monday" in page.locator("#trend-title").inner_text(), "The trend title should reflect the default Monday selection."
    assert page.locator(".trend-point").count() == 16, "Shift view should show 16 hourly points across four units."


def test_tooltip_shows_expected_heatmap_details(browser_page):
    page = browser_page
    target = page.locator('.heatmap-cell[data-weekday="Friday"][data-shift="Evening"]')
    target.hover()

    tooltip_text = page.locator("#tooltip").inner_text(timeout=5000)
    assert "Friday • Evening Shift" in tooltip_text, "Tooltip should name the hovered weekday and shift."
    assert "Average gap: 7.00" in tooltip_text, "Tooltip should show the formatted average staffing gap."
    assert "Peak hour: 7:00 PM" in tooltip_text, "Tooltip should show the peak hour for the hovered cell."
    assert "Required staff total: 212" in tooltip_text, "Tooltip should show the required staff total."
    assert "Units above 4: Emergency, ICU, Pediatrics, Surgery" in tooltip_text, "Tooltip should list the impacted units."


def test_clicking_a_cell_updates_the_trend_panel(browser_page):
    page = browser_page
    page.locator('.heatmap-cell[data-weekday="Friday"][data-shift="Evening"]').click()
    page.wait_for_timeout(250)

    assert page.locator(".heatmap-cell.selected").get_attribute("data-weekday") == "Friday", "Cell selection should move to Friday."
    assert page.locator(".heatmap-cell.selected").get_attribute("data-shift") == "Evening", "Cell selection should move to the Evening shift."
    assert page.locator("#selection-chip").inner_text() == "Shift view", "Selecting a single cell should keep the panel in shift view."
    assert page.locator("#trend-title").inner_text() == "Friday • Evening Shift", "The trend title should update to the clicked shift."
    assert page.locator(".trend-line").count() == 4, "The trend chart should keep one line per unit."
    assert page.locator(".trend-point").count() == 16, "A single shift selection should show four hours for each of four units."


def test_clicking_a_weekday_label_switches_to_day_overview(browser_page, expected_data):
    page = browser_page
    page.locator('.weekday-label[data-weekday="Sunday"]').click()
    page.wait_for_timeout(250)

    assert page.locator("#selection-chip").inner_text() == "Day overview", "Clicking a weekday label should switch to day overview mode."
    assert page.locator("#trend-title").inner_text() == "Sunday • Day Overview", "The trend title should indicate the day overview."
    assert page.locator(".heatmap-cell.row-selected").count() == 3, "A selected weekday row should highlight all three shift cells."
    assert page.locator(".trend-point").count() == 48, "Day overview should show twelve hours for each of four units."

    sunday_emergency = [
        float(row["staffing_gap"])
        for row in expected_data["trend"]
        if row["weekday"] == "Sunday" and row["unit"] == "Emergency"
    ]
    expected_average = sum(sunday_emergency) / len(sunday_emergency)
    card_text = page.locator('[data-unit-card="Emergency"]').inner_text()

    assert f"{expected_average:.2f}" in card_text, "The day overview detail card should update using the selected weekday data."
    assert "Peak hour: 7:00 PM" in card_text, "The Emergency detail card should show the latest Sunday peak hour."


def test_day_overview_can_return_to_shift_view(browser_page):
    page = browser_page
    page.locator('.heatmap-cell[data-weekday="Tuesday"][data-shift="Night"]').click()
    page.wait_for_timeout(250)

    assert page.locator("#selection-chip").inner_text() == "Shift view", "Clicking a cell after row mode should return to shift view."
    assert page.locator(".heatmap-cell.selected").get_attribute("data-weekday") == "Tuesday", "Selection should move back to the clicked cell weekday."
    assert page.locator(".heatmap-cell.selected").get_attribute("data-shift") == "Night", "Selection should move back to the clicked cell shift."
    assert page.locator(".heatmap-cell.row-selected").count() == 0, "Row highlight should clear when a specific cell is selected."


def test_output_data_row_counts_match_dashboard_inputs(expected_data):
    assert len(expected_data["heatmap"]) == 21, f"Expected 21 heatmap rows, found {len(expected_data['heatmap'])}."
    assert len(expected_data["trend"]) == 336, f"Expected 336 unit-hour rows, found {len(expected_data['trend'])}."
