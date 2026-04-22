#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

from common import CHROMIUM_EXECUTABLE_PATH, DECK_HTML_PATH, REQUIRED_ROLES, VIEWPORTS


BROWSER_PROBE = """
() => {
  const slides = Array.from(document.querySelectorAll('[data-slide-role][data-slide-index]'));
  const activeSlides = slides.filter((slide) => slide.classList.contains('active'));
  const dots = Array.from(document.querySelectorAll('[data-active-slide-indicator] span, .indicator span'));
  const activeDots = dots
    .map((dot, index) => dot.classList.contains('active') ? index : -1)
    .filter((index) => index >= 0);
  const activeSlide = activeSlides[0] ?? null;
  const describe = (element) => {
    if (!element) return 'unknown';
    const parts = [element.tagName.toLowerCase()];
    const slideRole = element.getAttribute('data-slide-role');
    const slideIndex = element.getAttribute('data-slide-index');
    if (slideRole) parts.push(`[role="${slideRole}"]`);
    if (slideIndex) parts.push(`[index="${slideIndex}"]`);
    if (element.id) parts.push(`#${element.id}`);
    const className = String(element.className || '').trim();
    if (className) parts.push(`.${className.replace(/\\s+/g, '.')}`);
    return parts.join('');
  };

  const result = {
    activeCount: activeSlides.length,
    activeRole: activeSlide ? activeSlide.getAttribute('data-slide-role') || '' : '',
    activeIndex: activeSlide ? Number(activeSlide.getAttribute('data-slide-index')) : -1,
    activeDotCount: activeDots.length,
    activeDotIndex: activeDots.length === 1 ? activeDots[0] : -1,
    navButtonsVisible: false,
    titleVisible: false,
    scrollOverflow: false,
    widthOverflow: false,
    offenders: [],
  };

  const prev = document.querySelector('[data-nav-prev]');
  const next = document.querySelector('[data-nav-next]');
  if (prev && next) {
    const prevRect = prev.getBoundingClientRect();
    const nextRect = next.getBoundingClientRect();
    result.navButtonsVisible = (
      prevRect.width > 0 &&
      prevRect.height > 0 &&
      nextRect.width > 0 &&
      nextRect.height > 0 &&
      prevRect.bottom <= window.innerHeight + 1 &&
      nextRect.bottom <= window.innerHeight + 1
    );
  }

  if (!activeSlide) {
    return result;
  }

  const title = activeSlide.querySelector('h1, h2, h3');
  if (title) {
    const titleRect = title.getBoundingClientRect();
    result.titleVisible = titleRect.width > 0 && titleRect.height > 0;
  }

  result.scrollOverflow = (
    activeSlide.scrollHeight > activeSlide.clientHeight + 1 ||
    activeSlide.scrollWidth > activeSlide.clientWidth + 1
  );
  result.widthOverflow = activeSlide.scrollWidth > activeSlide.clientWidth + 1;

  const slideRect = activeSlide.getBoundingClientRect();
  const nodes = Array.from(activeSlide.querySelectorAll('*'));
  for (const node of nodes) {
    const style = window.getComputedStyle(node);
    if (style.display === 'none' || style.visibility === 'hidden' || style.position === 'fixed') {
      continue;
    }
    const rect = node.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) {
      continue;
    }
    const outside = (
      rect.left < slideRect.left - 1 ||
      rect.right > slideRect.right + 1 ||
      rect.top < slideRect.top - 1 ||
      rect.bottom > slideRect.bottom + 1
    );
    if (outside) {
      result.offenders.push(describe(node));
      if (result.offenders.length >= 5) {
        break;
      }
    }
  }

  return result;
}
"""


def check_viewport(page, viewport: dict[str, int | str]) -> list[str]:
    width = int(viewport["width"])
    height = int(viewport["height"])
    label = str(viewport["name"])
    failures: list[str] = []

    page.set_viewport_size({"width": width, "height": height})
    page.goto(Path(DECK_HTML_PATH).resolve().as_uri(), wait_until="load")
    page.wait_for_timeout(200)

    state = page.evaluate(BROWSER_PROBE)
    if state["activeCount"] != 1 or state["activeIndex"] != 0:
        failures.append(f"{label}: initial active slide is invalid")
    if state["activeDotCount"] != 1 or state["activeDotIndex"] != 0:
        failures.append(f"{label}: initial active indicator is invalid")
    if not state["navButtonsVisible"]:
        failures.append(f"{label}: navigation buttons are not fully visible")

    for expected_index, expected_role in enumerate(REQUIRED_ROLES):
        if expected_index == 0:
            current = state
        else:
            page.keyboard.press("ArrowRight")
            page.wait_for_timeout(120)
            current = page.evaluate(BROWSER_PROBE)

        if current["activeCount"] != 1:
            failures.append(f"{label}: expected exactly one active slide at {expected_index}")
        if current["activeIndex"] != expected_index or current["activeRole"] != expected_role:
            failures.append(
                f"{label}: active slide mismatch at {expected_index} "
                f"(got index={current['activeIndex']} role={current['activeRole']!r})"
            )
        if current["activeDotCount"] != 1 or current["activeDotIndex"] != expected_index:
            failures.append(f"{label}: indicator mismatch at slide {expected_index}")
        if not current["titleVisible"]:
            failures.append(f"{label}: slide {expected_index} title is not visible")
        if current["scrollOverflow"] or current["widthOverflow"]:
            failures.append(f"{label}: slide {expected_index} overflows its viewport")
        if current["offenders"]:
            offenders = ", ".join(current["offenders"])
            failures.append(f"{label}: slide {expected_index} has out-of-bounds elements: {offenders}")

    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(100)
    after_last = page.evaluate(BROWSER_PROBE)
    if after_last["activeIndex"] != len(REQUIRED_ROLES) - 1:
        failures.append(f"{label}: ArrowRight should clamp at the last slide")

    page.click("[data-nav-prev]")
    page.wait_for_timeout(100)
    previous = page.evaluate(BROWSER_PROBE)
    if previous["activeIndex"] != len(REQUIRED_ROLES) - 2:
        failures.append(f"{label}: Previous button did not navigate backward")

    page.click("[data-nav-next]")
    page.wait_for_timeout(100)
    recovered = page.evaluate(BROWSER_PROBE)
    if recovered["activeIndex"] != len(REQUIRED_ROLES) - 1:
        failures.append(f"{label}: Next button did not navigate forward")

    return failures


def main() -> None:
    failures: list[str] = []
    with sync_playwright() as playwright:
        launch_kwargs = {
            "headless": True,
            "args": ["--no-sandbox", "--disable-dev-shm-usage"],
        }
        chromium_path = Path(CHROMIUM_EXECUTABLE_PATH)
        if chromium_path.exists():
            launch_kwargs["executable_path"] = str(chromium_path)
        browser = playwright.chromium.launch(**launch_kwargs)
        try:
            page = browser.new_page()
            for viewport in VIEWPORTS:
                failures.extend(check_viewport(page, viewport))
        finally:
            browser.close()

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        raise SystemExit(1)

    print("OK: browser contract passed for both QA viewports")


if __name__ == "__main__":
    main()
