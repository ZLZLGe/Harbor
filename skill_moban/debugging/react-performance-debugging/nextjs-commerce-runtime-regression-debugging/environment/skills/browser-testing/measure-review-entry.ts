import { chromium, devices } from 'playwright';

interface ReviewEntryResult {
  url: string;
  label: string | null;
  cls: number;
  console: string[];
}

async function measureReviewEntry(url: string): Promise<ReviewEntryResult> {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    ...devices['iPhone 13'],
    ignore_https_errors: true,
  });
  const page = await context.newPage();
  const consoleMessages: string[] = [];

  page.on('console', (message) => {
    if (message.type() === 'warning' || message.type() === 'error') {
      consoleMessages.push(message.text());
    }
  });

  await page.addInitScript(() => {
    localStorage.setItem('reader-active-shelf', 'gothic-fiction');
    localStorage.setItem(
      'reader-review-context',
      JSON.stringify({
        shelf: 'gothic-fiction',
        savedAt: Date.now(),
      }),
    );
    (window as typeof window & { __cls?: number }).__cls = 0;
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (!entry.hadRecentInput) {
          (window as typeof window & { __cls?: number }).__cls =
            ((window as typeof window & { __cls?: number }).__cls ?? 0) + entry.value;
        }
      }
    }).observe({ type: 'layout-shift', buffered: true });
  });

  await page.goto(url, { waitUntil: 'networkidle' });
  await page.waitForTimeout(700);

  const label = await page.locator('[data-testid="active-shelf-label"]').textContent();
  const cls = await page.evaluate(() => (window as typeof window & { __cls?: number }).__cls ?? 0);

  await browser.close();

  return {
    url,
    label,
    cls: Math.round(cls * 1000) / 1000,
    console: consoleMessages,
  };
}

const url = process.argv[2] || 'http://localhost:3000/?shelf=category-romance';

measureReviewEntry(url)
  .then((result) => console.log(JSON.stringify(result, null, 2)))
  .catch((error) => {
    console.error('Review entry measurement failed:', error.message);
    process.exit(1);
  });
