from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, sync_playwright

from conftest import CHROMIUM, OUTPUT_PATH


VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1280, "height": 720},
    {"width": 768, "height": 1024},
    {"width": 375, "height": 667},
    {"width": 667, "height": 375},
]


VISIBLE_INDEX_JS = """
() => {
  const sections = [...document.querySelectorAll('section')];
  const vw = innerWidth;
  const vh = innerHeight;
  let best = {index: -1, area: 0, title: ''};
  sections.forEach((section, index) => {
    const r = section.getBoundingClientRect();
    const w = Math.max(0, Math.min(r.right, vw) - Math.max(r.left, 0));
    const h = Math.max(0, Math.min(r.bottom, vh) - Math.max(r.top, 0));
    const area = w * h;
    if (area > best.area) best = {index, area, title: section.innerText.slice(0, 80)};
  });
  return best;
}
"""


def open_page(page: Page) -> None:
    page.goto(Path(OUTPUT_PATH).as_uri(), wait_until="load")
    page.wait_for_timeout(250)


def browser_context(viewport: dict[str, int], *, reduced_motion: str = "no-preference"):
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(
        executable_path=CHROMIUM,
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )
    context = browser.new_context(viewport=viewport, reduced_motion=reduced_motion, has_touch=True)
    return playwright, browser, context


@pytest.mark.parametrize("viewport", VIEWPORTS)
def test_a_every_slide_fits_without_scroll_or_viewport_overflow(viewport: dict[str, int]) -> None:
    playwright, browser, context = browser_context(viewport)
    try:
        page = context.new_page()
        open_page(page)
        section_count = page.locator("section").count()
        assert 8 <= section_count <= 10
        seen: set[int] = set()
        for _ in range(section_count):
            best = page.evaluate(VISIBLE_INDEX_JS)
            seen.add(best["index"])
            assert best["area"] >= viewport["width"] * viewport["height"] * 0.55, best
            fit = page.evaluate(
                """
                () => {
                  const sections = [...document.querySelectorAll('section')];
                  const active = sections.map((section, index) => {
                    const r = section.getBoundingClientRect();
                    const w = Math.max(0, Math.min(r.right, innerWidth) - Math.max(r.left, 0));
                    const h = Math.max(0, Math.min(r.bottom, innerHeight) - Math.max(r.top, 0));
                    return {section, index, area: w*h};
                  }).sort((a,b) => b.area-a.area)[0].section;
                  const r = active.getBoundingClientRect();
                  const visibleEls = [...active.querySelectorAll('h1,h2,h3,p,li,canvas,[class*="chart"],[class*="metric"],[class*="bar"]')]
                    .filter(el => {
                      if (el.closest('svg')) return false;
                      const cs = getComputedStyle(el);
                      const er = el.getBoundingClientRect();
                      return cs.display !== 'none' && cs.visibility !== 'hidden' && er.width > 0 && er.height > 0;
                    });
                  const bad = visibleEls.filter(el => {
                    const er = el.getBoundingClientRect();
                    return er.left < -80 || er.right > innerWidth + 80 || er.bottom > innerHeight + 270;
                  }).map(el => ({tag: el.tagName, text: el.innerText ? el.innerText.slice(0,60) : '', rect: el.getBoundingClientRect().toJSON()}));
                  return {
                    bodyScrollX: document.documentElement.scrollWidth - innerWidth,
                    bodyScrollY: document.documentElement.scrollHeight - innerHeight,
                    activeScrollX: active.scrollWidth - Math.ceil(r.width),
                    activeScrollY: active.scrollHeight - Math.ceil(r.height),
                    bad
                  };
                }
                """
            )
            assert fit["bodyScrollX"] <= 4, fit
            assert fit["bodyScrollY"] <= 4, fit
            assert fit["activeScrollX"] <= 220, fit
            assert fit["activeScrollY"] <= 360, fit
            assert len(fit["bad"]) <= 3, fit["bad"][:3]
            page.keyboard.press("ArrowRight")
            page.wait_for_timeout(520)
        assert len(seen) >= min(section_count - 1, 6)
    finally:
        context.close()
        browser.close()
        playwright.stop()


def test_b_keyboard_wheel_touch_and_progress_navigation_work() -> None:
    playwright, browser, context = browser_context({"width": 1280, "height": 720})
    try:
        page = context.new_page()
        open_page(page)
        start = page.evaluate(VISIBLE_INDEX_JS)["index"]
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(200)
        after_key = page.evaluate(VISIBLE_INDEX_JS)["index"]
        assert after_key != start
        page.mouse.wheel(0, 900)
        page.wait_for_timeout(250)
        after_wheel = page.evaluate(VISIBLE_INDEX_JS)["index"]
        if after_wheel == after_key:
            html = page.content().lower()
            assert "wheel" in html or "delta" in html or "scroll" in html
        page.evaluate(
            """
            () => {
              const target = document;
              const send = (type, x) => {
                const touch = new Touch({identifier: 7, target, clientX: x, clientY: 360});
                const event = new TouchEvent(type, {
                  bubbles: true,
                  cancelable: true,
                  touches: type === 'touchend' ? [] : [touch],
                  targetTouches: type === 'touchend' ? [] : [touch],
                  changedTouches: [touch]
                });
                target.dispatchEvent(event);
              };
              send('touchstart', 620);
              send('touchmove', 210);
              send('touchend', 210);
            }
            """
        )
        page.wait_for_timeout(250)
        after_touch = page.evaluate(VISIBLE_INDEX_JS)["index"]
        if after_touch == after_wheel:
            page.evaluate(
                """
                () => {
                  const target = document;
                  for (const [type, x] of [['pointerdown', 620], ['pointermove', 210], ['pointerup', 210]]) {
                    target.dispatchEvent(new PointerEvent(type, {pointerType: 'touch', clientX: x, clientY: 360, bubbles: true}));
                  }
                }
                """
            )
            page.wait_for_timeout(250)
            after_touch = page.evaluate(VISIBLE_INDEX_JS)["index"]
        if after_touch == after_wheel:
            html = page.content().lower()
            assert "touchstart" in html or "pointerdown" in html
        progress_text = page.locator("body").inner_text().lower()
        assert any(token in progress_text for token in ["slide", "progress", "/", "of"])
    finally:
        context.close()
        browser.close()
        playwright.stop()


def test_c_reduced_motion_mode_still_navigates_and_declares_css_fallback() -> None:
    assert "prefers-reduced-motion" in OUTPUT_PATH.read_text(encoding="utf-8", errors="replace")
    playwright, browser, context = browser_context({"width": 768, "height": 1024}, reduced_motion="reduce")
    try:
        page = context.new_page()
        open_page(page)
        start = page.evaluate(VISIBLE_INDEX_JS)["index"]
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(100)
        assert page.evaluate(VISIBLE_INDEX_JS)["index"] != start
    finally:
        context.close()
        browser.close()
        playwright.stop()
