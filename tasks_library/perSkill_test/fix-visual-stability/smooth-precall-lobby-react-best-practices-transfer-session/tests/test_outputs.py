import json
from pathlib import Path

import subprocess
from playwright.sync_api import sync_playwright


REPORT_PATH = Path("/app/output/precall-lobby-stability-report.json")
REQUIRED_CHECK_IDS = {
    "preview-frame-slot",
    "network-notice-slot",
    "participant-rail-slot",
    "permission-card-skeleton",
    "device-preference-bootstrap",
}


def test_app_responds_200():
    result = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:3000"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.stdout == "200"


def test_report_file_has_expected_checks():
    assert REPORT_PATH.exists(), "Missing output/precall-lobby-stability-report.json"
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

    assert report.get("lobby") == "precall-readiness"
    assert report.get("status") == "stable"
    assert report.get("preHydrationBootstrap") == {
        "cameraMode": "pre-hydration",
        "micMode": "pre-hydration",
    }

    checks = report.get("checks")
    assert isinstance(checks, list) and checks

    seen_ids = set()
    for check in checks:
        assert isinstance(check, dict)
        assert check.get("status") == "fixed"
        assert check.get("strategy")
        seen_ids.add(check.get("id"))

    assert REQUIRED_CHECK_IDS.issubset(seen_ids)


def test_inline_bootstrap_applies_device_preferences_before_hydration():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.add_init_script(
            """
            localStorage.setItem('precall-camera-mode', 'camera-off');
            localStorage.setItem('precall-mic-mode', 'mic-muted');
            """
        )
        page.goto("http://localhost:3000", wait_until="domcontentloaded")

        bootstrap_present = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('script')).some((script) => {
                const content = script.textContent || '';
                return content.includes('precall-camera-mode') &&
                    content.includes('precall-mic-mode') &&
                    content.includes('data-camera-mode') &&
                    content.includes('data-mic-mode');
            })
            """
        )
        attrs = page.evaluate(
            """
            () => ({
                camera: document.documentElement.getAttribute('data-camera-mode'),
                mic: document.documentElement.getAttribute('data-mic-mode')
            })
            """
        )
        browser.close()

    assert bootstrap_present, "Expected inline preference bootstrap in <head>"
    assert attrs == {"camera": "camera-off", "mic": "mic-muted"}


def test_network_slot_keeps_preview_shell_anchor():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1400})
        page.goto("http://localhost:3000", wait_until="domcontentloaded")

        slot_box = page.locator("[data-testid='network-slot']").bounding_box()
        before = page.locator("[data-testid='preview-shell']").bounding_box()
        page.wait_for_timeout(1800)
        after = page.locator("[data-testid='preview-shell']").bounding_box()
        browser.close()

    assert slot_box is not None
    assert slot_box["height"] >= 80
    assert before is not None
    assert after is not None
    assert abs(after["y"] - before["y"]) < 4


def test_preview_stage_keeps_its_footprint_when_media_arrives():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1400})
        page.goto("http://localhost:3000", wait_until="domcontentloaded")

        before = page.locator("[data-testid='preview-stage']").bounding_box()
        page.wait_for_timeout(1200)
        after = page.locator("[data-testid='preview-stage']").bounding_box()
        browser.close()

    assert before is not None
    assert after is not None
    assert abs(after["height"] - before["height"]) < 8
    assert abs(after["width"] - before["width"]) < 8


def test_participant_rail_reserves_main_column_width():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1400})
        page.goto("http://localhost:3000", wait_until="domcontentloaded")

        before = page.locator("[data-testid='main-column']").bounding_box()
        page.wait_for_timeout(2000)
        after = page.locator("[data-testid='main-column']").bounding_box()
        row_count = page.locator("[data-testid='participant-row']").count()
        browser.close()

    assert before is not None
    assert after is not None
    assert abs(after["width"] - before["width"]) < 8
    assert row_count == 5


def test_permission_cards_hold_join_footer_position():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1400})
        page.goto("http://localhost:3000", wait_until="domcontentloaded")

        before = page.locator("[data-testid='join-footer']").bounding_box()
        page.wait_for_timeout(1400)
        after = page.locator("[data-testid='join-footer']").bounding_box()
        card_count = page.locator("[data-testid='permission-card']").count()
        browser.close()

    assert before is not None
    assert after is not None
    assert abs(after["y"] - before["y"]) < 6
    assert card_count == 3


def test_device_toggles_still_persist_to_local_storage():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:3000", wait_until="networkidle")

        page.locator("[data-testid='camera-toggle']").click()
        page.locator("[data-testid='mic-toggle']").click()

        state = page.evaluate(
            """
            () => ({
                camera: document.documentElement.getAttribute('data-camera-mode'),
                mic: document.documentElement.getAttribute('data-mic-mode'),
                storedCamera: localStorage.getItem('precall-camera-mode'),
                storedMic: localStorage.getItem('precall-mic-mode')
            })
            """
        )
        browser.close()

    assert state == {
        "camera": "camera-off",
        "mic": "mic-muted",
        "storedCamera": "camera-off",
        "storedMic": "mic-muted",
    }


def test_cls_stays_below_budget_during_lobby_boot():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1400})
        page.add_init_script(
            """
            window.__cls = 0;
            let currentWindowScore = 0;
            let windowStart = 0;
            let lastShiftTime = 0;

            new PerformanceObserver((list) => {
              for (const entry of list.getEntries()) {
                if (entry.hadRecentInput) {
                  continue;
                }

                const timestamp = entry.startTime / 1000;
                const startsNewWindow =
                  windowStart === 0 ||
                  (timestamp - lastShiftTime) > 1 ||
                  (timestamp - windowStart) > 5;

                if (startsNewWindow) {
                  currentWindowScore = 0;
                  windowStart = timestamp;
                }

                currentWindowScore += entry.value;
                lastShiftTime = timestamp;
                window.__cls = Math.max(window.__cls, currentWindowScore);
              }
            }).observe({ type: 'layout-shift', buffered: true });
            """
        )

        page.goto("http://localhost:3000", wait_until="networkidle")
        page.wait_for_timeout(2200)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)
        cls_value = page.evaluate("window.__cls")
        browser.close()

    assert cls_value < 0.1, f"CLS was {cls_value}"
