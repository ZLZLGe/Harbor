import { chromium, devices } from './playwright-runtime';

interface ProfileResult {
  name: string;
  label: string | null;
  drawerTitle: string | null;
  linkedContextText: string | null;
  linkedContextInDrawer: boolean;
  cls: number;
  console: string[];
}

interface DeeplinkResult {
  url: string;
  profiles: ProfileResult[];
}

async function measureProfile(
  url: string,
  name: string,
  contextOptions: Record<string, unknown>,
): Promise<ProfileResult> {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    ignore_https_errors: true,
    ...contextOptions,
  });
  const page = await context.newPage();
  const consoleMessages: string[] = [];

  page.on('console', (message) => {
    if (message.type() === 'warning' || message.type() === 'error') {
      consoleMessages.push(message.text());
    }
  });

  await page.addInitScript(() => {
    localStorage.setItem('dashboard-active-filter', 'europe');
    localStorage.setItem(
      'dashboard-context',
      JSON.stringify({
        filterId: 'europe',
        savedAt: Date.now() - 60_000,
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

  const label = await page.locator('[data-testid="active-filter-label"]').textContent();
  const drawerTitle = await page.locator('[data-testid="alert-drawer-title"]').textContent();
  const linkedContext = page.locator('[data-testid="linked-alert-context"]');
  const linkedContextText = (await linkedContext.count()) > 0 ? await linkedContext.textContent() : null;
  const linkedContextInDrawer =
    (await linkedContext.count()) > 0
      ? await linkedContext.evaluate((node) => Boolean(node.closest('[data-testid="alert-drawer"]')))
      : false;
  const cls = await page.evaluate(() => (window as typeof window & { __cls?: number }).__cls ?? 0);

  await browser.close();

  return {
    name,
    label,
    drawerTitle,
    linkedContextText,
    linkedContextInDrawer,
    cls: Math.round(cls * 1000) / 1000,
    console: consoleMessages,
  };
}

async function measureDashboardDeeplink(url: string): Promise<DeeplinkResult> {
  const profiles = await Promise.all([
    measureProfile(url, 'iphone-13', {
      ...devices['iPhone 13'],
    }),
    measureProfile(url, 'tablet-820', {
      viewport: { width: 820, height: 1180 },
      is_mobile: false,
      user_agent:
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36',
    }),
  ]);

  return {
    url,
    profiles,
  };
}

const url = process.argv[2] || 'http://localhost:3000/?filter=north-america&alert=retention-drop-na';

measureDashboardDeeplink(url)
  .then((result) => console.log(JSON.stringify(result, null, 2)))
  .catch((error) => {
    console.error('Dashboard deeplink measurement failed:', error.message);
    process.exit(1);
  });
