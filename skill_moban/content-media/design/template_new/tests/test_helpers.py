from __future__ import annotations

import hashlib
import http.server
import json
import os
import socketserver
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

ANSWER_DIR = Path(os.environ.get("TASK_ANSWER_DIR", "/root/answer"))
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/root/environment/data"))
DECK_ENTRYPOINT = Path(
    os.environ.get("TASK_DECK_ENTRYPOINT", "/root/environment/deck/build_briefing.py")
)
REGISTRY_LOG = Path(
    os.environ.get("SOURCE_REGISTRY_LOG_PATH", "/tmp/source-registry-requests.log")
)
PREVIEW_ROOT = Path(
    os.environ.get("STYLE_PREVIEW_ROOT", "/root/.ecc-design/slide-previews")
)
PREVIEW_ROOT_ALT = Path(
    os.environ.get("STYLE_PREVIEW_ROOT_ALT", "/root/environment/deck/.ecc-design/slide-previews")
)
REGISTRY_URL = os.environ.get("SOURCE_REGISTRY_URL", "http://127.0.0.1:4873")
HTTP_PORT = int(os.environ.get("TASK_HTTP_PORT", "8765"))

_SERVER = None
_SERVER_THREAD = None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ensure_built() -> None:
    subprocess.run(
        ["python3", str(DECK_ENTRYPOINT), "--output", str(ANSWER_DIR)],
        check=True,
    )


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def start_answer_server() -> str:
    global _SERVER, _SERVER_THREAD
    if _SERVER is not None:
        return f"http://127.0.0.1:{HTTP_PORT}/presentation.html"

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            return

    os.chdir(ANSWER_DIR)
    _SERVER = socketserver.TCPServer(("127.0.0.1", HTTP_PORT), QuietHandler)
    _SERVER_THREAD = threading.Thread(target=_SERVER.serve_forever, daemon=True)
    _SERVER_THREAD.start()
    return f"http://127.0.0.1:{HTTP_PORT}/presentation.html"


def stop_answer_server() -> None:
    global _SERVER, _SERVER_THREAD
    if _SERVER is not None:
      _SERVER.shutdown()
      _SERVER.server_close()
      _SERVER = None
      _SERVER_THREAD = None


def browser_snapshot(viewport: dict[str, int], reduced_motion: str = "no-preference") -> dict[str, Any]:
    url = start_answer_server()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport=viewport, reduced_motion=reduced_motion)
        page = context.new_page()
        requests: list[str] = []
        console: list[str] = []
        page.on("request", lambda req: requests.append(req.url))
        page.on("console", lambda msg: console.append(f"{msg.type}: {msg.text}"))
        page.goto(url, wait_until="load", timeout=30000)
        page.wait_for_timeout(200)
        result = page.evaluate(
            """
            () => {
              const slideCandidates = Array.from(document.querySelectorAll('[data-slide], section.slide, main > section'));
              const slides = slideCandidates.filter((slide) => {
                const style = window.getComputedStyle(slide);
                return style.display !== 'none';
              });
              const semanticActive = slides.find((slide) => {
                return slide.classList.contains('is-active')
                  || slide.getAttribute('aria-hidden') === 'false'
                  || slide.getAttribute('data-active') === 'true';
              });
              const activeSlide = semanticActive || slides.find((slide) => {
                const rect = slide.getBoundingClientRect();
                const style = window.getComputedStyle(slide);
                return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && parseFloat(style.opacity || '1') > 0.25;
              }) || slides[0] || null;
              const overflow = slides.map((slide) => {
                const rect = slide.getBoundingClientRect();
                const main = slide.querySelector('[data-role=\"slide-main\"]') || slide;
                const footer = slide.querySelector('.footer-line') || slide.lastElementChild || slide;
                const mainStyle = window.getComputedStyle(main);
                return {
                  id: slide.id || null,
                  scrollHeight: slide.scrollHeight,
                  clientHeight: slide.clientHeight,
                  rectTop: rect.top,
                  rectBottom: rect.bottom,
                  rectHeight: rect.height,
                  footerBottom: footer.getBoundingClientRect().bottom,
                  overflowY: mainStyle.overflowY,
                  textLength: slide.innerText.trim().length
                };
              });
              const sourceNodes = Array.from(document.querySelectorAll('[data-source-id]')).map((node) => ({
                sourceId: node.getAttribute('data-source-id'),
                text: node.textContent.trim(),
                href: node.getAttribute('href') || null,
              }));
              return {
                bodyScrollHeight: document.documentElement.scrollHeight,
                bodyClientHeight: document.documentElement.clientHeight,
                scrollY: window.scrollY,
                slideCount: slides.length,
                activeSlideId: activeSlide ? activeSlide.id : null,
                activeSlideText: activeSlide ? activeSlide.innerText.slice(0, 140) : '',
                progressText: (document.querySelector('#progress-text, [data-progress-text], .slide-progress') || {}).textContent || '',
                hasCanvas: document.querySelectorAll('canvas').length,
                hasFullBleedImageOnly: slides.some((slide) => {
                  const children = Array.from(slide.children);
                  return children.length > 0 && children.every((child) => ['IMG', 'CANVAS', 'SVG'].includes(child.tagName));
                }),
                sourceNodes,
                overflow,
                remoteRefs: Array.from(document.querySelectorAll('link[href], script[src], img[src], iframe[src], source[src]')).map((node) => {
                  const attr = node.getAttribute('href') || node.getAttribute('src');
                  return attr || '';
                }).filter((value) => /^https?:\\/\\//i.test(value)),
              };
            }
            """
        )
        screenshot_name = f"deck-{viewport['width']}x{viewport['height']}-{reduced_motion}.png"
        Path("/logs/verifier").mkdir(parents=True, exist_ok=True)
        page.screenshot(path=f"/logs/verifier/{screenshot_name}", full_page=True)
        context.close()
        browser.close()
        result["requests"] = requests
        result["console"] = console
        return result


def navigation_probe() -> dict[str, Any]:
    url = start_answer_server()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            has_touch=True,
        )
        page = context.new_page()
        page.goto(url, wait_until="load", timeout=30000)
        page.wait_for_timeout(200)

        def active_state() -> dict[str, Any]:
            return page.evaluate(
                """
                () => {
                  const slides = Array.from(document.querySelectorAll('[data-slide], section.slide, main > section'));
                  const semanticActive = slides.find((slide) => {
                    return slide.classList.contains('is-active')
                      || slide.getAttribute('aria-hidden') === 'false'
                      || slide.getAttribute('data-active') === 'true';
                  });
                  const active = semanticActive || slides.find((slide) => {
                    const style = getComputedStyle(slide);
                    const rect = slide.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && parseFloat(style.opacity || '1') > 0.25;
                  }) || slides[0];
                  return {
                    id: active ? active.id : null,
                    progress: (document.querySelector('#progress-text, [data-progress-text], .slide-progress') || {}).textContent || '',
                    scrollY: window.scrollY,
                    hash: window.location.hash
                  };
                }
                """
            )

        initial = active_state()
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(420)
        after_key = active_state()
        page.mouse.wheel(0, 900)
        page.wait_for_timeout(420)
        after_wheel = active_state()
        page.dispatch_event(
            "body",
            "touchstart",
            {
                "touches": [{"identifier": 1, "clientX": 560, "clientY": 300}],
                "changedTouches": [{"identifier": 1, "clientX": 560, "clientY": 300}],
            },
        )
        page.dispatch_event(
            "body",
            "touchend",
            {
                "touches": [],
                "changedTouches": [{"identifier": 1, "clientX": 180, "clientY": 300}],
            },
        )
        page.wait_for_timeout(420)
        after_touch = active_state()
        browser.close()
        return {
            "initial": initial,
            "after_key": after_key,
            "after_wheel": after_wheel,
            "after_touch": after_touch,
        }
