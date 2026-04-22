import { chromium } from './playwright-runtime';

interface InteractionResult {
  url: string;
  activeDelta: number;
  probeRuns: number;
}

async function measureInteractions(url: string): Promise<InteractionResult> {
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
    (window as typeof window & { __reviewPulseRuns?: number }).__reviewPulseRuns = 0;
  });

  await page.goto(url, { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="shelf-search"]');

  const baseActive = await page.evaluate(() => (window as typeof window & { __runtimeStats?: { active: number } }).__runtimeStats?.active ?? 0);
  const tabs = [
    'gothic-fiction',
    'category-romance',
    'category-adventure',
    'category-classics-of-literature',
  ];

  for (let index = 0; index < 18; index += 1) {
    await page.locator(`[data-testid="shelf-tab-${tabs[index % tabs.length]}"]`).click();
    await page.locator('[data-testid="shelf-search"]').fill(index % 2 === 0 ? 'dark' : '');
    await page.waitForTimeout(50);
  }

  await page.evaluate(() => {
    (window as typeof window & { __reviewPulseRuns?: number }).__reviewPulseRuns = 0;
    for (let i = 0; i < 5; i += 1) {
      window.dispatchEvent(new Event('catalog:heartbeat'));
    }
  });

  const activeAfter = await page.evaluate(() => (window as typeof window & { __runtimeStats?: { active: number } }).__runtimeStats?.active ?? 0);
  const probeRuns = await page.evaluate(() => (window as typeof window & { __reviewPulseRuns?: number }).__reviewPulseRuns ?? 0);

  await browser.close();

  return {
    url,
    activeDelta: activeAfter - baseActive,
    probeRuns,
  };
}

const url = process.argv[2] || 'http://localhost:3000/?shelf=category-classics-of-literature';

measureInteractions(url)
  .then((result) => console.log(JSON.stringify(result, null, 2)))
  .catch((error) => {
    console.error('Interaction measurement failed:', error.message);
    process.exit(1);
  });
