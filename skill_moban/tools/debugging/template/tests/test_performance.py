import time

import httpx
import pytest

try:
    from playwright.sync_api import Browser, Page
except ModuleNotFoundError:  # pragma: no cover - local host-side API-only verification
    Browser = Page = object


BASE = "http://localhost:3000"


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
        current_label = page.locator('[data-testid="active-filter-label"]').text_content().strip()
        seen_labels.append(current_label)
        assert current_label == expected_label, (
            f"Active filter drifted during the stability window: {' -> '.join(seen_labels)}"
        )
        if time.monotonic() >= deadline:
            return
        page.wait_for_timeout(interval_ms)


def assert_alert_deeplink_is_stable(browser: Browser, *, viewport: dict, is_mobile: bool, user_agent: str | None):
    context = browser.new_context(
        viewport=viewport,
        is_mobile=is_mobile,
        user_agent=user_agent,
        ignore_https_errors=True,
    )
    page = context.new_page()
    console_messages = []

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
    assert page.locator('[data-testid="alert-drawer-title"]').text_content().strip() == "Retention drop in North America"
    assert page.evaluate("window.__cls") < 0.05
    assert not any("persisted dashboard context" in entry.lower() for entry in console_messages)

    page.reload(wait_until="networkidle")
    page.wait_for_timeout(200)
    assert_filter_label_stays(page, "North America", duration_ms=900)
    assert page.locator('[data-testid="alert-drawer-title"]').text_content().strip() == "Retention drop in North America"
    context.close()


@pytest.mark.asyncio
async def test_dashboard_api_uses_real_snapshot():
    async with httpx.AsyncClient(timeout=30.0) as client:
        start = time.time()
        response = await client.get(f"{BASE}/api/dashboard")
        elapsed = (time.time() - start) * 1000

    assert response.status_code == 200
    payload = response.json()
    assert elapsed >= 180, f"/api/dashboard returned too quickly ({elapsed:.0f}ms) to prove the downstream simulator was exercised"
    assert payload["snapshotId"] == "analytics-dashboard-2026-04-09"
    assert len(payload["alerts"]) >= 4, "Analytics payload is unexpectedly small"
    assert any(alert["title"] == "Retention drop in North America" for alert in payload["alerts"])
    assert any(point["filterId"] == "north-america" for point in payload["timeline"])


def test_homepage_renders_real_dashboard_and_alert_drawer(page: Page):
    page.goto(f"{BASE}/?filter=north-america", wait_until="networkidle")

    content = page.content()
    assert "Retention drop in North America" in content
    assert "Checkout latency spike in Europe" in content
    assert "Open alert" in content

    page.locator('[data-testid="open-alert-retention-drop-na"]').click()
    page.locator('[data-testid="alert-drawer"]').wait_for()
    assert page.locator('[data-testid="alert-drawer-title"]').text_content().strip() == "Retention drop in North America"


def test_alert_deeplink_stays_stable_across_profiles(browser: Browser):
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


def test_dashboard_requests_noncritical_code_on_demand(page: Page):
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
    assert pre_click_urls == initial_urls, "Dashboard fetched extra JS before advanced insights was opened"
    assert late_urls, "Opening advanced insights should trigger at least one new JS request"


def test_repeated_dashboard_interactions_keep_runtime_steady(page: Page):
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

    assert active_after - base_active <= 6, f"Runtime handlers leaked across repeated dashboard interactions (delta={active_after - base_active})"
    assert pulse_runs <= 20, f"Runtime follow-up work fanned out too aggressively after repeated interactions (runs={pulse_runs})"
    assert refresh_ms <= 260, f"Timeline refresh stayed too expensive after the soak sequence (refreshMs={refresh_ms})"


def test_advanced_insights_panel_still_renders(page: Page):
    page.goto(f"{BASE}/", wait_until="networkidle")
    page.locator('[data-testid="toggle-advanced-insights"]').click()
    page.locator('[data-testid="advanced-insights-panel"]').wait_for()
    assert page.locator('[data-testid="advanced-insights-panel"]').count() == 1
