import csv
import json
import os

import pytest
from playwright.sync_api import sync_playwright

OUTPUT_HTML = "/root/output/elevation-profile.html"
SAMPLES_CSV = "/root/data/trail-samples.csv"
WAYPOINTS_JSON = "/root/data/trail-waypoints.json"
LEGEND_LABELS = [
    "0-3.9% 平缓",
    "4-7.9% 持续爬升",
    "8-11.9% 陡坡",
    "12%+ 冲顶段",
]


def load_samples():
    with open(SAMPLES_CSV, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                "distance_km": float(row["distance_km"]),
                "elevation_m": int(row["elevation_m"]),
                "grade_pct": float(row["grade_pct"]),
            }
            for row in reader
        ]


def load_waypoints():
    with open(WAYPOINTS_JSON, encoding="utf-8") as handle:
        return json.load(handle)


def highest_waypoint(waypoints):
    return max(waypoints, key=lambda item: (item["elevation_m"], item["distance_km"]))


def hover_hotspot(page, index):
    hotspot = page.locator(".sample-hotspot").nth(index)
    hotspot.hover(force=True)
    page.wait_for_timeout(200)


def read_legend_labels(page):
    return page.eval_on_selector_all(
        "#slope-legend > *",
        "nodes => nodes.map(node => node.textContent.trim())",
    )


@pytest.fixture(scope="module")
def expected_samples():
    return load_samples()


@pytest.fixture(scope="module")
def expected_waypoints():
    return load_waypoints()


@pytest.fixture(scope="module")
def browser_page():
    import http.server
    import socketserver
    import threading

    if not os.path.exists(OUTPUT_HTML):
        pytest.fail(f"Primary output file missing: {OUTPUT_HTML}")

    port = 8771
    handler = http.server.SimpleHTTPRequestHandler
    original_dir = os.getcwd()
    os.chdir("/root/output")
    server = socketserver.TCPServer(("", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1500, "height": 1200})
        page.goto(f"http://127.0.0.1:{port}/elevation-profile.html", wait_until="load")
        page.wait_for_selector("#profile-chart svg")
        page.wait_for_selector(".profile-segment")
        page.wait_for_selector("#waypoint-list button")
        page.wait_for_timeout(1200)

        os.makedirs("/logs/verifier", exist_ok=True)
        page.screenshot(path="/logs/verifier/elevation-profile.png", full_page=True)

        yield page

        browser.close()

    server.shutdown()
    os.chdir(original_dir)


def test_primary_output_exists():
    assert os.path.isfile(OUTPUT_HTML), f"Expected {OUTPUT_HTML} to exist"
    assert os.path.getsize(OUTPUT_HTML) > 5000, "Output HTML is unexpectedly small"


def test_renders_profile_segments_legend_and_waypoints(browser_page, expected_samples, expected_waypoints):
    page = browser_page
    assert page.locator(".profile-segment").count() == len(expected_samples) - 1, (
        "Profile line should be segmented between each pair of adjacent samples"
    )
    assert page.locator(".sample-hotspot").count() == len(expected_samples), (
        "Each sample point should expose a hover hotspot"
    )
    assert page.locator("#waypoint-list button").count() == len(expected_waypoints), (
        "Waypoint list should render one button per waypoint"
    )

    assert page.locator("#slope-legend > *").count() == 4, "Legend should contain the fixed four slope bins"
    assert read_legend_labels(page) == LEGEND_LABELS, "Legend labels must match the required slope bins"


def test_initial_selection_uses_highest_elevation_waypoint(browser_page, expected_waypoints):
    page = browser_page
    highest = highest_waypoint(expected_waypoints)

    selected_button = page.locator('#waypoint-list button[aria-pressed="true"]')
    assert selected_button.count() == 1, "Exactly one waypoint button should be selected by default"
    selected_text = selected_button.inner_text()
    assert highest["name"] in selected_text, "Default selection should use the highest-elevation waypoint"

    detail_text = page.locator("#waypoint-detail").inner_text()
    assert highest["name"] in detail_text, "Waypoint detail panel should show the selected waypoint name"
    assert f'{highest["distance_km"]:.1f} km' in detail_text, "Waypoint detail should show distance"
    assert f'{highest["elevation_m"]} m' in detail_text, "Waypoint detail should show elevation"
    assert highest["category"] in detail_text, "Waypoint detail should show category"
    assert highest["eta"] in detail_text, "Waypoint detail should show ETA"
    assert highest["note"] in detail_text, "Waypoint detail should show the waypoint note"

    selected_marker = page.locator(".waypoint-marker.is-selected")
    assert selected_marker.count() == 1, "Exactly one waypoint marker should be highlighted"
    assert selected_marker.get_attribute("data-waypoint-id") == highest["id"], (
        "Selected profile marker should match the highest waypoint"
    )


def test_clicking_waypoint_updates_detail_and_marker(browser_page, expected_waypoints):
    page = browser_page
    target = next(item for item in expected_waypoints if item["id"] == "ridge-camp")

    page.locator("#waypoint-list button", has_text=target["name"]).first.click()
    page.wait_for_timeout(200)

    selected_button = page.locator('#waypoint-list button[aria-pressed="true"]')
    assert selected_button.count() == 1, "Clicking a waypoint should keep selection unique"
    assert target["name"] in selected_button.inner_text(), "Clicked waypoint button should become selected"

    selected_marker = page.locator(".waypoint-marker.is-selected")
    assert selected_marker.get_attribute("data-waypoint-id") == target["id"], (
        "Clicked waypoint should highlight the matching profile marker"
    )

    detail_text = page.locator("#waypoint-detail").inner_text()
    assert target["name"] in detail_text, "Waypoint detail panel should update after clicking a waypoint"
    assert f'{target["distance_km"]:.1f} km' in detail_text, "Updated detail should include clicked waypoint distance"
    assert f'{target["elevation_m"]} m' in detail_text, "Updated detail should include clicked waypoint elevation"
    assert target["category"] in detail_text, "Updated detail should include clicked waypoint category"
    assert target["eta"] in detail_text, "Updated detail should include clicked waypoint ETA"
    assert target["note"] in detail_text, "Updated detail should include clicked waypoint note"


def test_hover_shows_fixed_tooltip_and_crosshair(browser_page, expected_samples):
    page = browser_page
    target = expected_samples[5]

    hover_hotspot(page, 5)

    tooltip = page.locator('[role="tooltip"]')
    opacity = tooltip.evaluate("node => parseFloat(window.getComputedStyle(node).opacity)")
    assert opacity > 0.8, "Tooltip should be visible when hovering a sample hotspot"

    tooltip_lines = [line.strip() for line in tooltip.inner_text().splitlines() if line.strip()]
    assert tooltip_lines == [
        f'距离: {target["distance_km"]:.1f} km',
        f'海拔: {target["elevation_m"]} m',
        f'坡度: {target["grade_pct"]:.1f}%',
    ], "Tooltip content must use the required three-line format"

    crosshair_opacity = page.eval_on_selector_all(
        "#crosshair-x, #crosshair-y, #hover-focus",
        "nodes => nodes.map(node => parseFloat(window.getComputedStyle(node).opacity || '0'))",
    )
    assert all(value > 0.5 for value in crosshair_opacity), (
        "Hovering a sample hotspot should reveal both crosshair lines and the focus marker"
    )


def test_profile_uses_multiple_segment_colors(browser_page):
    page = browser_page
    segment_colors = page.eval_on_selector_all(
        ".profile-segment",
        """
        nodes => nodes.map(node => {
          const style = window.getComputedStyle(node);
          return style.stroke || node.getAttribute('stroke');
        })
        """,
    )
    assert len(set(segment_colors)) == 4, "Profile segments should use four distinct colors for the slope bins"
