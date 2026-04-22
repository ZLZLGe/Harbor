import time

import httpx
import pytest
from playwright.sync_api import Browser, Page


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
          window.__reviewPulseRuns = 0;
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


def assert_shelf_label_stays(page: Page, expected_label: str, *, duration_ms: int = 1000, interval_ms: int = 125):
    seen_labels = []
    deadline = time.monotonic() + duration_ms / 1000

    while True:
        current_label = page.locator('[data-testid="active-shelf-label"]').text_content().strip()
        seen_labels.append(current_label)
        assert current_label == expected_label, (
            f"Active shelf drifted during the stability window: {' -> '.join(seen_labels)}"
        )
        if time.monotonic() >= deadline:
            return
        page.wait_for_timeout(interval_ms)


def assert_review_entry_is_stable(browser: Browser, *, viewport: dict, is_mobile: bool, user_agent: str | None):
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
        localStorage.setItem('reader-active-shelf', 'gothic-fiction');
        localStorage.setItem(
          'reader-review-context',
          JSON.stringify({
            shelf: 'gothic-fiction',
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

    page.goto(f"{BASE}/?shelf=category-romance", wait_until="networkidle")
    page.wait_for_timeout(200)
    assert_shelf_label_stays(page, "Category: Romance", duration_ms=1200)
    assert page.evaluate("window.__cls") < 0.05
    assert not any("persisted review context" in entry.lower() for entry in console_messages)

    page.reload(wait_until="networkidle")
    page.wait_for_timeout(200)
    assert_shelf_label_stays(page, "Category: Romance", duration_ms=900)
    context.close()


@pytest.mark.asyncio
async def test_books_api_uses_real_snapshot():
    async with httpx.AsyncClient(timeout=30.0) as client:
        start = time.time()
        response = await client.get(f"{BASE}/api/books")
        elapsed = (time.time() - start) * 1000

    assert response.status_code == 200
    payload = response.json()["books"]
    assert elapsed >= 150, f"/api/books returned too quickly ({elapsed:.0f}ms) to prove the downstream simulator was exercised"
    assert len(payload) >= 8, "Catalog payload is unexpectedly small"
    assert any(book["title"] == "Frankenstein; or, the modern prometheus" for book in payload)
    assert any(book["title"] == "Pride and Prejudice" for book in payload)


def test_homepage_renders_real_books_and_shortlist(page: Page):
    page.goto(f"{BASE}/?shelf=category-classics-of-literature", wait_until="networkidle")

    content = page.content()
    assert "Frankenstein; or, the modern prometheus" in content
    assert "Pride and Prejudice" in content
    assert "Pin to shortlist" in content

    page.locator('[data-testid^="save-book-"]').first.click()
    page.wait_for_timeout(150)
    assert page.locator('[data-testid="shortlist-count"]').text_content().strip() == "1"


def test_review_entry_stays_stable_across_mobile_profiles(browser: Browser):
    assert_review_entry_is_stable(
        browser,
        viewport={"width": 390, "height": 844},
        is_mobile=True,
        user_agent=(
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        ),
    )
    assert_review_entry_is_stable(
        browser,
        viewport={"width": 820, "height": 1180},
        is_mobile=False,
        user_agent=None,
    )


def test_compare_review_flow_requests_noncritical_code_on_demand(page: Page):
    _, js_order = collect_page_js(page)

    page.goto(f"{BASE}/compare", wait_until="networkidle")
    page.wait_for_selector('[data-testid="tab-overview"]')
    page.wait_for_timeout(250)
    initial_urls = list(dict.fromkeys(js_order))
    page.wait_for_timeout(400)
    pre_click_urls = list(dict.fromkeys(js_order))

    page.locator('[data-testid="tab-advanced"]').click()
    page.locator('[data-testid="advanced-content"]').wait_for()
    page.wait_for_timeout(350)

    late_urls = [url for url in dict.fromkeys(js_order) if url not in pre_click_urls]
    assert pre_click_urls == initial_urls, "Compare page fetched extra JS before advanced analysis was opened"
    assert late_urls, "Opening the advanced review tab should trigger at least one new JS request"


def test_repeated_review_interactions_keep_runtime_steady(page: Page):
    install_runtime_probe(page)
    page.goto(f"{BASE}/?shelf=category-classics-of-literature", wait_until="networkidle")
    page.wait_for_selector('[data-testid="shelf-search"]')

    base_active = page.evaluate("window.__runtimeStats.active")
    tabs = [
        "gothic-fiction",
        "category-romance",
        "category-adventure",
        "category-classics-of-literature",
    ]

    for index in range(18):
        page.locator(f'[data-testid="shelf-tab-{tabs[index % len(tabs)]}"]').click()
        page.fill('[data-testid="shelf-search"]', "dark" if index % 2 == 0 else "")
        page.wait_for_timeout(50)

    page.evaluate("window.__reviewPulseRuns = 0")
    page.evaluate(
        """
        for (let i = 0; i < 5; i += 1) {
          window.dispatchEvent(new Event('catalog:heartbeat'));
        }
        """
    )

    active_after = page.evaluate("window.__runtimeStats.active")
    probe_runs = page.evaluate("window.__reviewPulseRuns")

    assert active_after - base_active <= 6, f"Runtime handlers leaked across repeated review interactions (delta={active_after - base_active})"
    assert probe_runs <= 20, f"Runtime follow-up work fanned out too aggressively after repeated interactions (runs={probe_runs})"


def test_compare_advanced_tab_still_renders(page: Page):
    page.goto(f"{BASE}/compare", wait_until="networkidle")
    page.locator('[data-testid="tab-advanced"]').click()
    page.locator('[data-testid="advanced-content"]').wait_for()
    assert page.locator('[data-testid="advanced-content"]').count() == 1
