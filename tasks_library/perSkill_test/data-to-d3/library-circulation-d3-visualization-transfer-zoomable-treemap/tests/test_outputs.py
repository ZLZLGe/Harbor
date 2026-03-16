import csv
import os
from collections import defaultdict
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path("/root/output")
HTML_FILE = OUTPUT_DIR / "circulation-treemap.html"
D3_FILE = OUTPUT_DIR / "js" / "d3.v6.min.js"
DATA_FILE = OUTPUT_DIR / "data" / "library_circulation.csv"


@pytest.fixture(scope="module")
def expected_data():
    with DATA_FILE.open(newline="") as handle:
        rows = list(csv.DictReader(handle))

    for row in rows:
        for key in ("annual_checkouts", "unique_titles", "renewals"):
            row[key] = int(row[key])
        row["avg_wait_days"] = float(row["avg_wait_days"])

    branch_totals = defaultdict(int)
    for row in rows:
        branch_totals[row["branch"]] += row["annual_checkouts"]

    return {"rows": rows, "branch_totals": dict(branch_totals)}


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
        page = browser.new_page(viewport={"width": 1480, "height": 1180})
        page.goto(f"http://127.0.0.1:{port}/circulation-treemap.html", wait_until="load", timeout=30000)
        page.wait_for_selector("svg rect", timeout=15000)
        page.wait_for_timeout(700)

        log_dir = Path("/logs/verifier")
        log_dir.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(log_dir / "circulation-treemap.png"), full_page=True)

        yield page

        browser.close()

    server.shutdown()
    os.chdir(original_cwd)


def tile_locator(page, label):
    return page.locator("svg g.tile").filter(has=page.locator("rect")).filter(
        has=page.locator("text", has_text=label)
    ).first


def test_required_files_exist(expected_data):
    assert HTML_FILE.exists(), f"Expected HTML output at {HTML_FILE}"
    assert D3_FILE.exists(), f"Expected local D3 bundle at {D3_FILE}"
    assert DATA_FILE.exists(), f"Expected copied dataset at {DATA_FILE}"
    assert len(expected_data["rows"]) == 20, f"Expected 20 circulation rows, found {len(expected_data['rows'])}."


def test_root_view_renders_branch_tiles_and_breadcrumb(browser_page, expected_data):
    page = browser_page
    assert "Library Circulation" in page.title(), "The page title should describe the circulation explorer."
    assert page.locator("svg rect").count() == 5, "The initial treemap view should show five branch tiles."
    assert page.get_by_text("All Branches").count() >= 1, "The breadcrumb trail should include the root label."

    svg_text = page.locator("svg").inner_text()
    for branch in expected_data["branch_totals"]:
        assert branch in svg_text, f"Expected root label for branch '{branch}' in the treemap."

    assert "1,892,750" in page.locator("body").inner_text(), "The page should show the total annual circulation summary."


def test_branch_tooltip_summarizes_root_tile(browser_page):
    page = browser_page
    tile = tile_locator(page, "Central Library")
    tile.hover()
    tooltip_text = page.locator("#tooltip").inner_text(timeout=5000)

    assert "Central Library" in tooltip_text, "Branch tooltip should include the branch name."
    assert "Neighborhood: Civic Center" in tooltip_text, "Branch tooltip should include the neighborhood."
    assert "Annual checkouts: 597,000" in tooltip_text, "Branch tooltip should include the aggregated branch total."
    assert "Dominant genre: Fiction" in tooltip_text, "Branch tooltip should include the dominant genre."


def test_clicking_branch_zooms_to_genres_and_updates_breadcrumb(browser_page):
    page = browser_page
    tile = tile_locator(page, "Central Library")
    tile.click()
    page.wait_for_timeout(450)

    breadcrumb_text = page.locator("#breadcrumb").inner_text()
    assert "All Branches" in breadcrumb_text and "Central Library" in breadcrumb_text, "Zoomed view should update the breadcrumb trail."
    assert page.locator("svg rect").count() == 4, "Zooming into Central Library should show four genre tiles."

    svg_text = page.locator("svg").inner_text()
    for genre in ("Fiction", "Mystery", "Children", "Digital Media"):
        assert genre in svg_text, f"Expected zoomed treemap label for genre '{genre}'."

    page.get_by_text("All Branches").first.click(force=True)
    page.wait_for_timeout(450)
    assert page.locator("svg rect").count() == 5, "Returning through the breadcrumb should restore the branch-level view."


def test_genre_tooltip_shows_leaf_metrics(browser_page):
    page = browser_page
    tile_locator(page, "Central Library").click()
    page.wait_for_timeout(450)

    tile_locator(page, "Children").hover()
    tooltip_text = page.locator("#tooltip").inner_text(timeout=5000)

    assert "Central Library / Children" in tooltip_text, "Leaf tooltip should include the branch and genre path."
    assert "Audience: Youth" in tooltip_text, "Leaf tooltip should include the genre audience."
    assert "Annual checkouts: 159,600" in tooltip_text, "Leaf tooltip should include genre annual checkouts."
    assert "Unique titles: 27,410" in tooltip_text, "Leaf tooltip should include unique title counts."
    assert "Renewals: 29,890" in tooltip_text, "Leaf tooltip should include renewal counts."

    page.get_by_text("All Branches").first.click(force=True)
    page.wait_for_timeout(450)


def test_labels_remain_visible_after_zoom(browser_page):
    page = browser_page
    root_svg_text = page.locator("svg").inner_text()
    assert "597,000" in root_svg_text, "The branch-level labels should include formatted circulation totals."

    tile_locator(page, "Harbor Point Branch").click()
    page.wait_for_timeout(450)
    zoomed_svg_text = page.locator("svg").inner_text()

    assert "Children" in zoomed_svg_text, "Zoomed labels should include the genre names."
    assert "112,300" in zoomed_svg_text, "Zoomed labels should include formatted genre totals."
