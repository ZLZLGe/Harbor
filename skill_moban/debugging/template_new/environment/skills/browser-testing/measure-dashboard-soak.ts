import { chromium } from './playwright-runtime';

interface SoakResult {
  url: string;
  activeDelta: number;
  pulseRuns: number;
  refreshMs: number;
}

async function measureDashboardSoak(url: string): Promise<SoakResult> {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  await page.addInitScript(() => {
    const stats = { added: 0, removed: 0, active: 0 };
    const counts = new WeakMap<EventListenerOrEventListenerObject, number>();
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

    (window as typeof window & { __runtimeStats?: typeof stats }).__runtimeStats = stats;
    (window as typeof window & { __dashboardPulseRuns?: number }).__dashboardPulseRuns = 0;
    (window as typeof window & { __lastTimelineRefreshMs?: number }).__lastTimelineRefreshMs = 0;
  });

  await page.goto(url, { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="timeline-refresh"]');

  const baseActive = await page.evaluate(() => (window as typeof window & { __runtimeStats?: { active: number } }).__runtimeStats?.active ?? 0);
  const filters = ['all-regions', 'north-america', 'europe', 'apac'];
  const alertForFilter: Record<string, string> = {
    'all-regions': 'retention-drop-na',
    'north-america': 'retention-drop-na',
    'europe': 'checkout-latency-eu',
    'apac': 'mobile-bounce-apac',
  };

  for (let index = 0; index < 18; index += 1) {
    const currentFilter = filters[index % filters.length];
    await page.locator(`[data-testid="filter-tab-${currentFilter}"]`).click();
    await page.waitForTimeout(40);
    await page.locator(`[data-testid="open-alert-${alertForFilter[currentFilter]}"]`).click();
    await page.locator('[data-testid="close-alert-drawer"]').click();
    await page.locator('[data-testid="timeline-refresh"]').click();
    await page.waitForTimeout(60);
  }

  await page.evaluate(() => {
    (window as typeof window & { __dashboardPulseRuns?: number }).__dashboardPulseRuns = 0;
    for (let i = 0; i < 5; i += 1) {
      window.dispatchEvent(new Event('dashboard:heartbeat'));
    }
  });

  const activeAfter = await page.evaluate(() => (window as typeof window & { __runtimeStats?: { active: number } }).__runtimeStats?.active ?? 0);
  const pulseRuns = await page.evaluate(() => (window as typeof window & { __dashboardPulseRuns?: number }).__dashboardPulseRuns ?? 0);
  const refreshMs = await page.evaluate(() => (window as typeof window & { __lastTimelineRefreshMs?: number }).__lastTimelineRefreshMs ?? 0);

  await browser.close();

  return {
    url,
    activeDelta: activeAfter - baseActive,
    pulseRuns,
    refreshMs,
  };
}

const url = process.argv[2] || 'http://localhost:3000';

measureDashboardSoak(url)
  .then((result) => console.log(JSON.stringify(result, null, 2)))
  .catch((error) => {
    console.error('Dashboard soak measurement failed:', error.message);
    process.exit(1);
  });
