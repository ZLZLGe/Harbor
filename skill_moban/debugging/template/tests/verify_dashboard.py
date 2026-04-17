import hashlib
import json
import sys
import time
import traceback
import urllib.request
from pathlib import Path

from playwright.sync_api import Browser, Page, sync_playwright


BASE = "http://localhost:3000"


def ensure(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


def _sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def install_runtime_probe(page: Page):
    page.add_init_script(
        """
        (() => {
          const stats = { added: 0, removed: 0, active: 0 };
          const counts = new WeakMap();
          const add = EventTarget.prototype.addEventListener;
          const remove = EventTarget.prototype.removeEventListener;

          EventTarget.prototype.addEventListener = function(type, listener, options) {
            if ((this === window || this === document) && typeof listener === 'function') {
              const current = counts.get(listener) || 0;
              counts.set(listener, current + 1);
              stats.added += 1;
              stats.active += 1;
            }
            return add.call(this, type, listener, options);
          };

          EventTarget.prototype.removeEventListener = function(type, listener, options) {
            if ((this === window || this === document) && typeof listener === 'function') {
              const current = counts.get(listener) || 0;
              if (current > 0) {
                if (current === 1) {
                  counts.delete(listener);
                } else {
                  counts.set(listener, current - 1);
                }
                stats.removed += 1;
                stats.active -= 1;
              }
            }
            return remove.call(this, type, listener, options);
          };

          window.__runtimeStats = stats;
          window.__dashboardPulseRuns = 0;
          window.__lastTimelineRefreshMs = 0;
        })();
        """
    )


def collect_page_js(page: Page):
    js_sizes = {}
    js_order = []

    def handle_response(response):
        if not response.url.startswith(BASE) or response.status != 200:
            return
        content_type = response.headers.get("content-type", "")
        if ".js" not in response.url and "javascript" not in content_type:
            return
        try:
            body = response.body()
        except Exception:
            return
        js_order.append(response.url)
        js_sizes[response.url] = len(body)

    page.on("response", handle_response)
    return js_sizes, js_order


def assert_filter_label_stays(page: Page, expected_label: str, *, duration_ms: int = 1000, interval_ms: int = 125):
    seen_labels = []
    deadline = time.monotonic() + duration_ms / 1000

    while True:
        current_label = (page.locator('[data-testid="active-filter-label"]').text_content() or "").strip()
        seen_labels.append(current_label)
        ensure(
            current_label == expected_label,
            f"Active filter drifted during the stability window: {' -> '.join(seen_labels)}",
        )
        if time.monotonic() >= deadline:
            return
        page.wait_for_timeout(interval_ms)


def verify_hidden_dashboard_simulator_not_modified():
    expected = {
        "/services/api-simulator/src/server.ts": "a169c7dc10af41b2c28754c2fdbb4cdd60f84bfcc57e88d85aae258348901292",
        "/services/api-simulator/data/analytics_snapshot.json": "62182698bee81e108ca755692aad00e6514f7b86d9d22be60d0102059a3b7693",
    }

    for path, checksum in expected.items():
        ensure(_sha256(path) == checksum, f"Protected input changed: {path}")


def verify_solver_input_surface():
    hidden_paths = [
        "/root/incident_ticket.md",
        "/root/session_replay_notes.md",
        "/root/console_excerpt.log",
        "/root/runtime_observations.md",
        "/root/quality_manifest.json",
        "/root/analytics_snapshot.json",
        "/root/upstream_source_notice.md",
        "/root/network_home.har",
        "/root/network_compare.har",
        "/root/trace_home.json",
        "/root/trace_compare.json",
    ]
    for path in hidden_paths:
        ensure(not Path(path).exists(), f"Unexpected solver-visible artifact present: {path}")


def verify_repository_layout():
    repo_root = Path(__file__).resolve().parents[1]
    ensure(
        not (repo_root / "environment" / "assets").exists(),
        "Repository unexpectedly uses a generic environment/assets bucket",
    )


def verify_dashboard_api_uses_real_snapshot():
    start = time.monotonic()
    with urllib.request.urlopen(f"{BASE}/api/dashboard", timeout=30) as response:
        elapsed = (time.monotonic() - start) * 1000
        ensure(response.status == 200, f"/api/dashboard returned status {response.status}")
        payload = json.load(response)

    ensure(
        elapsed >= 180,
        f"/api/dashboard returned too quickly ({elapsed:.0f}ms) to prove the downstream simulator was exercised",
    )
    ensure(payload["snapshotId"] == "analytics-dashboard-2026-04-09", "Unexpected snapshot ID in API payload")
    ensure(len(payload["alerts"]) >= 4, "Analytics payload is unexpectedly small")
    ensure(
        any(alert["title"] == "Retention drop in North America" for alert in payload["alerts"]),
        "Retention alert missing from API payload",
    )
    ensure(
        any(point["filterId"] == "north-america" for point in payload["timeline"]),
        "Timeline payload missing north-america points",
    )


def verify_homepage_renders_real_dashboard_and_alert_drawer(browser: Browser):
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    try:
        page.goto(f"{BASE}/?filter=north-america", wait_until="networkidle")

        content = page.content()
        ensure("Retention drop in North America" in content, "Expected dashboard alert not rendered on homepage")
        ensure("Checkout latency spike in Europe" in content, "Expected Europe alert not rendered on homepage")
        ensure("Open alert" in content, "Dashboard alert CTA missing")

        page.locator('[data-testid="open-alert-retention-drop-na"]').click()
        page.locator('[data-testid="alert-drawer"]').wait_for()
        ensure(
            (page.locator('[data-testid="alert-drawer-title"]').text_content() or "").strip()
            == "Retention drop in North America",
            "Alert drawer title did not match the selected alert",
        )
    finally:
        context.close()


def assert_alert_deeplink_is_stable(browser: Browser, *, viewport: dict, is_mobile: bool, user_agent: str | None):
    context = browser.new_context(
        viewport=viewport,
        is_mobile=is_mobile,
        user_agent=user_agent,
        ignore_https_errors=True,
    )
    page = context.new_page()
    console_messages = []

    try:
        page.on(
            "console",
            lambda message: console_messages.append(message.text)
            if message.type in {"warning", "error"}
            else None,
        )
        page.add_init_script(
            """
            localStorage.setItem('dashboard-active-filter', 'europe');
            localStorage.setItem(
              'dashboard-context',
              JSON.stringify({
                filterId: 'europe',
                savedAt: Date.now() - 60_000,
              }),
            );
            window.__cls = 0;
            new PerformanceObserver((list) => {
              for (const entry of list.getEntries()) {
                if (!entry.hadRecentInput) {
                  window.__cls += entry.value;
                }
              }
            }).observe({ type: 'layout-shift', buffered: true });
            """
        )

        page.goto(f"{BASE}/?filter=north-america&alert=retention-drop-na", wait_until="networkidle")
        page.wait_for_timeout(200)
        assert_filter_label_stays(page, "North America", duration_ms=1200)
        ensure(
            (page.locator('[data-testid="alert-drawer-title"]').text_content() or "").strip()
            == "Retention drop in North America",
            "Alert drawer title was unstable on initial deeplink load",
        )
        ensure(page.evaluate("window.__cls") < 0.05, "CLS regression exceeded the threshold on alert deeplink")
        ensure(
            not any("persisted dashboard context" in entry.lower() for entry in console_messages),
            "Unexpected console noise indicated stale dashboard context reuse",
        )

        page.reload(wait_until="networkidle")
        page.wait_for_timeout(200)
        assert_filter_label_stays(page, "North America", duration_ms=900)
        ensure(
            (page.locator('[data-testid="alert-drawer-title"]').text_content() or "").strip()
            == "Retention drop in North America",
            "Alert drawer title changed after reload",
        )
    finally:
        context.close()


def verify_alert_deeplink_stays_stable_across_profiles(browser: Browser):
    assert_alert_deeplink_is_stable(
        browser,
        viewport={"width": 390, "height": 844},
        is_mobile=True,
        user_agent=(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        ),
    )
    assert_alert_deeplink_is_stable(
        browser,
        viewport={"width": 820, "height": 1180},
        is_mobile=False,
        user_agent=None,
    )


def verify_dashboard_requests_noncritical_code_on_demand(browser: Browser):
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    try:
        _, js_order = collect_page_js(page)

        page.goto(f"{BASE}/", wait_until="networkidle")
        page.wait_for_selector('[data-testid="toggle-advanced-insights"]')
        page.wait_for_timeout(250)
        initial_urls = list(dict.fromkeys(js_order))
        page.wait_for_timeout(400)
        pre_click_urls = list(dict.fromkeys(js_order))

        page.locator('[data-testid="toggle-advanced-insights"]').click()
        page.locator('[data-testid="advanced-insights-panel"]').wait_for()
        page.wait_for_timeout(350)

        late_urls = [url for url in dict.fromkeys(js_order) if url not in pre_click_urls]
        ensure(pre_click_urls == initial_urls, "Dashboard fetched extra JS before advanced insights was opened")
        ensure(late_urls, "Opening advanced insights should trigger at least one new JS request")
    finally:
        context.close()


def verify_repeated_dashboard_interactions_keep_runtime_steady(browser: Browser):
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    try:
        install_runtime_probe(page)
        page.goto(f"{BASE}/", wait_until="networkidle")
        page.wait_for_selector('[data-testid="timeline-refresh"]')

        base_active = page.evaluate("window.__runtimeStats.active")
        filters = [
            "all-regions",
            "north-america",
            "europe",
            "apac",
        ]
        alert_for_filter = {
            "all-regions": "retention-drop-na",
            "north-america": "retention-drop-na",
            "europe": "checkout-latency-eu",
            "apac": "mobile-bounce-apac",
        }

        for index in range(18):
            current_filter = filters[index % len(filters)]
            page.locator(f'[data-testid="filter-tab-{current_filter}"]').click()
            page.wait_for_timeout(40)
            page.locator(f'[data-testid="open-alert-{alert_for_filter[current_filter]}"]').click()
            page.locator('[data-testid="close-alert-drawer"]').click()
            page.locator('[data-testid="timeline-refresh"]').click()
            page.wait_for_timeout(60)

        page.evaluate("window.__dashboardPulseRuns = 0")
        page.evaluate(
            """
            for (let i = 0; i < 5; i += 1) {
              window.dispatchEvent(new Event('dashboard:heartbeat'));
            }
            """
        )

        active_after = page.evaluate("window.__runtimeStats.active")
        pulse_runs = page.evaluate("window.__dashboardPulseRuns")
        refresh_ms = page.evaluate("window.__lastTimelineRefreshMs")

        ensure(
            active_after - base_active <= 6,
            f"Runtime handlers leaked across repeated dashboard interactions (delta={active_after - base_active})",
        )
        ensure(
            pulse_runs <= 20,
            f"Runtime follow-up work fanned out too aggressively after repeated interactions (runs={pulse_runs})",
        )
        ensure(
            refresh_ms <= 260,
            f"Timeline refresh stayed too expensive after the soak sequence (refreshMs={refresh_ms})",
        )
    finally:
        context.close()


def verify_advanced_insights_panel_still_renders(browser: Browser):
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    try:
        page.goto(f"{BASE}/", wait_until="networkidle")
        page.locator('[data-testid="toggle-advanced-insights"]').click()
        page.locator('[data-testid="advanced-insights-panel"]').wait_for()
        ensure(
            page.locator('[data-testid="advanced-insights-panel"]').count() == 1,
            "Advanced insights panel failed to render exactly once",
        )
    finally:
        context.close()


def run_check(name: str, fn):
    print(f"=== {name} ===")
    try:
        fn()
    except Exception as exc:
        print(f"[FAIL] {name}: {exc}")
        traceback.print_exc()
        return False

    print(f"[PASS] {name}")
    return True


def main():
    checks = [
        ("hidden dashboard simulator not modified", verify_hidden_dashboard_simulator_not_modified),
        ("solver input surface does not expose incident artifacts", verify_solver_input_surface),
        ("repository layout does not use generic assets bucket", verify_repository_layout),
        ("dashboard API uses real snapshot", verify_dashboard_api_uses_real_snapshot),
    ]

    passed = 0
    failures = 0

    for name, fn in checks:
        if run_check(name, fn):
            passed += 1
        else:
            failures += 1

    browser_error = None
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            try:
                browser_checks = [
                    ("homepage renders real dashboard and alert drawer", lambda: verify_homepage_renders_real_dashboard_and_alert_drawer(browser)),
                    ("alert deeplink stays stable across profiles", lambda: verify_alert_deeplink_stays_stable_across_profiles(browser)),
                    ("dashboard requests noncritical code on demand", lambda: verify_dashboard_requests_noncritical_code_on_demand(browser)),
                    ("repeated dashboard interactions keep runtime steady", lambda: verify_repeated_dashboard_interactions_keep_runtime_steady(browser)),
                    ("advanced insights panel still renders", lambda: verify_advanced_insights_panel_still_renders(browser)),
                ]
                for name, fn in browser_checks:
                    if run_check(name, fn):
                        passed += 1
                    else:
                        failures += 1
            finally:
                browser.close()
    except Exception as exc:
        browser_error = exc

    if browser_error is not None:
        failed_names = [
            "homepage renders real dashboard and alert drawer",
            "alert deeplink stays stable across profiles",
            "dashboard requests noncritical code on demand",
            "repeated dashboard interactions keep runtime steady",
            "advanced insights panel still renders",
        ]
        for name in failed_names:
            print(f"=== {name} ===")
            print(f"[FAIL] {name}: {browser_error}")
            traceback.print_exception(browser_error)
        failures += len(failed_names)

    total = passed + failures
    print(f"Summary: {passed}/{total} checks passed")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
