from pathlib import Path
import subprocess

from playwright.sync_api import sync_playwright


APP_URL = "http://localhost:3000"
SOURCE_FILE = Path("/app/src/components/AnalyticsTable.tsx")
FORBIDDEN_LAYOUT_READS = [
    "getBoundingClientRect",
    "offsetWidth",
    "offsetHeight",
    "scrollHeight",
    "clientHeight",
]


class TestAnalyticsWorkspace:
    def test_app_responds_200(self):
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", APP_URL],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.stdout == "200", "The analytics workspace is not responding with HTTP 200"

    def test_workspace_navigation_still_works(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1200})
            page.goto(APP_URL, wait_until="networkidle")
            page.wait_for_selector('[data-testid="activity-row"]', timeout=5000)

            page.locator('[data-testid="view-overview"]').click()
            page.wait_for_timeout(150)
            overview_rows = page.locator('[data-testid="activity-row"]').count()

            page.locator('[data-testid="view-alerts"]').click()
            page.wait_for_timeout(150)
            alerts_rows = page.locator('[data-testid="activity-row"]').count()
            browser.close()

        assert overview_rows > 0, "Overview rows no longer render"
        assert alerts_rows > 0, "Alert rows no longer render"


class TestSourceConstraints:
    def test_no_layout_reads_in_component_source(self):
        source = SOURCE_FILE.read_text()
        for token in FORBIDDEN_LAYOUT_READS:
            assert token not in source, f"Avoid layout reads like {token} in AnalyticsTable.tsx"


class TestVirtualizedTable:
    def test_dom_row_count_stays_bounded_during_scroll(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1200})
            page.goto(APP_URL, wait_until="networkidle")
            page.wait_for_selector('[data-testid="activity-row"]', timeout=5000)

            initial_count = page.locator('[data-testid="activity-row"]').count()
            initial_mounted_value = int(page.locator('[data-testid="rows-mounted-value"]').inner_text())

            page.locator('[data-testid="activity-scroller"]').evaluate(
                """(node) => {
                    node.scrollTop = node.scrollHeight;
                    node.dispatchEvent(new Event('scroll'));
                }"""
            )
            page.wait_for_timeout(200)

            final_count = page.locator('[data-testid="activity-row"]').count()
            final_mounted_value = int(page.locator('[data-testid="rows-mounted-value"]').inner_text())
            final_ids = page.locator('[data-testid="activity-row"]').evaluate_all(
                "(nodes) => nodes.map((node) => node.getAttribute('data-row-id'))"
            )
            browser.close()

        assert initial_count <= 50, f"Expected a bounded number of mounted rows, got {initial_count}"
        assert initial_mounted_value <= 50, "Mounted rows summary should reflect a bounded window"
        assert final_count <= 50, f"Expected a bounded number of mounted rows after scroll, got {final_count}"
        assert final_mounted_value <= 50, "Mounted rows summary should stay bounded after scroll"
        assert "stream-240" in final_ids, "Virtualized scrolling should still reach the final activity rows"

    def test_summary_panels_stay_on_a_stable_grid_across_views(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1200})
            page.goto(APP_URL, wait_until="networkidle")
            page.wait_for_selector('[data-testid="summary-card-window"]', timeout=5000)

            activity_y = page.locator('[data-testid="summary-card-window"]').bounding_box()["y"]
            page.locator('[data-testid="view-overview"]').click()
            page.wait_for_timeout(150)
            overview_y = page.locator('[data-testid="summary-card-window"]').bounding_box()["y"]
            browser.close()

        assert abs(activity_y - overview_y) <= 6, "Summary panels should not jump between rows when switching views"
