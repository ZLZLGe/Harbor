import time

import httpx
import pytest
from playwright.sync_api import Page


BASE = "http://localhost:3000"


class TestPagePerformance:
    @pytest.mark.asyncio
    async def test_homepage_loads_fast(self):
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.get(BASE)
            start = time.time()
            response = await client.get(BASE)
            elapsed = (time.time() - start) * 1000
            assert response.status_code == 200
            assert elapsed < 850, f"Homepage took {elapsed:.0f}ms (should be <850ms)"

    @pytest.mark.asyncio
    async def test_homepage_has_primary_content(self):
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(BASE)
            assert "Package" in response.text


class TestAPIPerformance:
    @pytest.mark.asyncio
    async def test_collection_api_fast(self):
        async with httpx.AsyncClient(timeout=30.0) as client:
            start = time.time()
            response = await client.get(f"{BASE}/api/offers")
            elapsed = (time.time() - start) * 1000
            assert response.status_code == 200
            assert elapsed < 1000, f"Collection API took {elapsed:.0f}ms (should be <1000ms)"

    @pytest.mark.asyncio
    async def test_action_api_fast(self):
        async with httpx.AsyncClient(timeout=30.0) as client:
            start = time.time()
            response = await client.post(f"{BASE}/api/quote", json={})
            elapsed = (time.time() - start) * 1000
            assert response.status_code == 200
            assert elapsed < 850, f"Action API took {elapsed:.0f}ms (should be <850ms)"

    @pytest.mark.asyncio
    async def test_external_service_still_used(self):
        async with httpx.AsyncClient(timeout=30.0) as client:
            start = time.time()
            response = await client.post(f"{BASE}/api/quote", json={})
            elapsed = (time.time() - start) * 1000
            assert response.status_code == 200
            assert elapsed >= 380, f"Action API too fast ({elapsed:.0f}ms) - external service may have been bypassed"


class TestClientPerformance:
    def test_rerender_count_is_limited(self, page: Page):
        page.goto(BASE)
        page.wait_for_selector('[data-testid="shortlist-count"]')
        page.evaluate("performance.clearMarks()")

        buttons = page.locator('[data-testid^="shortlist-offer-"]')
        for index in range(min(5, buttons.count())):
            buttons.nth(index).click()
            page.wait_for_timeout(100)

        render_count = page.evaluate("performance.getEntriesByType('mark').length")
        assert render_count > 0, "No render marks detected"
        assert render_count < 50, f"Too many rerenders: {render_count}"


class TestBundleOptimization:
    def test_analysis_page_initial_bundle_small(self, page: Page):
        js_bytes = []

        def handle_response(response):
            if response.url.endswith('.js') and response.status == 200:
                try:
                    js_bytes.append(len(response.body()))
                except Exception:
                    pass

        page.on('response', handle_response)
        page.goto(f"{BASE}/analysis")
        page.wait_for_selector('[data-testid="tab-overview"]')

        total_js_kb = sum(js_bytes) / 1024
        assert total_js_kb < 400, f"Initial JS bundle is {total_js_kb:.0f}KB (should be <400KB)"


class TestFunctionality:
    def test_testids_preserved(self, page: Page):
        page.goto(BASE)
        assert page.locator('[data-testid="shortlist-count"]').count() > 0
        assert page.locator('[data-testid^="shortlist-offer-"]').count() > 0

        page.goto(f"{BASE}/analysis")
        assert page.locator('[data-testid="tab-overview"]').count() > 0
        assert page.locator('[data-testid="tab-advanced"]').count() > 0

    def test_primary_action_updates_count(self, page: Page):
        page.goto(BASE)
        page.wait_for_selector('[data-testid="shortlist-count"]')

        initial_text = page.locator('[data-testid="shortlist-count"]').text_content()
        assert "0" in initial_text

        page.locator('[data-testid^="shortlist-offer-"]').first.click()
        page.wait_for_timeout(200)

        updated_text = page.locator('[data-testid="shortlist-count"]').text_content()
        assert "1" in updated_text

    def test_analysis_advanced_tab_works(self, page: Page):
        page.goto(f"{BASE}/analysis")
        page.wait_for_selector('[data-testid="tab-overview"]')
        page.locator('[data-testid="tab-advanced"]').click()
        page.wait_for_timeout(500)
        assert page.locator('[data-testid="advanced-content"]').count() > 0

    def test_primary_content_is_visible(self, page: Page):
        page.goto(BASE)
        content = page.content()
        assert "Package" in content
        assert "Add to Shortlist" in content
        assert "$" in content
