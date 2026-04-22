import { chromium, devices } from './playwright-runtime';

interface DeeplinkProfileResult {
  name: string;
  label: string | null;
  drawerTitle: string | null;
  linkedContextText: string | null;
  linkedContextInDrawer: boolean;
  cls: number;
}

interface WaterfallResult {
  initialJs: string[];
  preClickJs: string[];
  lateJs: string[];
}

interface SoakResult {
  activeDelta: number;
  pulseRuns: number;
  refreshMs: number;
}

interface RegressionSummary {
  status: 'ok' | 'regressed';
  findings: string[];
  deeplink: {
    failingProfiles: string[];
    clsBreaches: string[];
    misplacedContextProfiles: string[];
    profiles: DeeplinkProfileResult[];
  };
  waterfall: WaterfallResult & {
    eagerJsBeforeOpen: string[];
  };
  soak: SoakResult & {
    eventLeak: boolean;
    pulseFanOut: boolean;
    slowRefresh: boolean;
  };
  hints: string[];
}

async function measureDeeplink(url: string): Promise<DeeplinkProfileResult[]> {
  const variants = [
    {
      name: 'iphone-13',
      options: {
        ...devices['iPhone 13'],
      },
    },
    {
      name: 'tablet-820',
      options: {
        viewport: { width: 820, height: 1180 },
        is_mobile: false,
        user_agent:
          'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36',
      },
    },
  ];

  return Promise.all(
    variants.map(async ({ name, options }) => {
      const browser = await chromium.launch();
      const context = await browser.newContext({
        ignore_https_errors: true,
        ...options,
      });
      const page = await context.newPage();

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

      await context.close();
      await browser.close();

      return {
        name,
        label,
        drawerTitle,
        linkedContextText,
        linkedContextInDrawer,
        cls: Math.round(cls * 1000) / 1000,
      };
    }),
  );
}

async function measureWaterfall(url: string): Promise<WaterfallResult> {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const jsOrder: string[] = [];

  page.on('response', (response) => {
    if (!response.url().startsWith(url.replace(/\/$/, ''))) {
      return;
    }
    const contentType = response.headers()['content-type'] ?? '';
    if (!response.url().includes('.js') && !contentType.includes('javascript')) {
      return;
    }
    jsOrder.push(response.url());
  });

  await page.goto(url, { waitUntil: 'networkidle' });
  await page.waitForSelector('[data-testid="toggle-advanced-insights"]');
  await page.waitForTimeout(250);
  const initialJs = [...new Set(jsOrder)];
  await page.waitForTimeout(400);
  const preClickJs = [...new Set(jsOrder)];
  await page.locator('[data-testid="toggle-advanced-insights"]').click();
  await page.locator('[data-testid="advanced-insights-panel"]').waitFor();
  await page.waitForTimeout(350);
  const lateJs = [...new Set(jsOrder)].filter((entry) => !preClickJs.includes(entry));

  await page.close();
  await browser.close();

  return {
    initialJs,
    preClickJs,
    lateJs,
  };
}

async function measureSoak(url: string): Promise<SoakResult> {
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
    europe: 'checkout-latency-eu',
    apac: 'mobile-bounce-apac',
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

  await page.close();
  await browser.close();

  return {
    activeDelta: activeAfter - baseActive,
    pulseRuns,
    refreshMs,
  };
}

function buildHints(summary: RegressionSummary): string[] {
  const hints: string[] = [];

  if (summary.deeplink.failingProfiles.length > 0) {
    hints.push('Cold-start filter drift still points to the deeplink / persisted-filter restoration path.');
  }
  if (summary.deeplink.misplacedContextProfiles.length > 0 || summary.deeplink.clsBreaches.length > 0) {
    hints.push('Drawer-scoped linked context is still unstable, so inspect alert-context rendering and viewport-specific timing.');
  }
  if (summary.waterfall.eagerJsBeforeOpen.length > 0 || summary.waterfall.lateJs.length === 0) {
    hints.push('Non-critical analysis code is still on the initial path, so inspect how the advanced panel import is triggered.');
  }
  if (summary.soak.eventLeak || summary.soak.pulseFanOut || summary.soak.slowRefresh) {
    hints.push('Long-session slowdown still points to dashboard probe wiring or refresh telemetry work that scales with interaction history.');
  }

  return hints;
}

async function main() {
  const homeUrl = process.argv[2] || 'http://localhost:3000';
  const deeplinkUrl =
    process.argv[3] || 'http://localhost:3000/?filter=north-america&alert=retention-drop-na';

  const [profiles, waterfall, soak] = await Promise.all([
    measureDeeplink(deeplinkUrl),
    measureWaterfall(homeUrl),
    measureSoak(homeUrl),
  ]);

  const failingProfiles = profiles
    .filter((profile) => profile.label !== 'North America' || profile.drawerTitle !== 'Retention drop in North America')
    .map((profile) => profile.name);
  const clsBreaches = profiles.filter((profile) => profile.cls >= 0.05).map((profile) => profile.name);
  const misplacedContextProfiles = profiles
    .filter((profile) => profile.linkedContextText && !profile.linkedContextInDrawer)
    .map((profile) => profile.name);
  const eagerJsBeforeOpen = waterfall.preClickJs.filter((entry) => !waterfall.initialJs.includes(entry));

  const summary: RegressionSummary = {
    status:
      failingProfiles.length > 0 ||
      clsBreaches.length > 0 ||
      misplacedContextProfiles.length > 0 ||
      eagerJsBeforeOpen.length > 0 ||
      waterfall.lateJs.length === 0 ||
      soak.activeDelta > 6 ||
      soak.pulseRuns > 20 ||
      soak.refreshMs > 260
        ? 'regressed'
        : 'ok',
    findings: [],
    deeplink: {
      failingProfiles,
      clsBreaches,
      misplacedContextProfiles,
      profiles,
    },
    waterfall: {
      ...waterfall,
      eagerJsBeforeOpen,
    },
    soak: {
      ...soak,
      eventLeak: soak.activeDelta > 6,
      pulseFanOut: soak.pulseRuns > 20,
      slowRefresh: soak.refreshMs > 260,
    },
    hints: [],
  };

  if (failingProfiles.length > 0) {
    summary.findings.push(`deeplink-filter-drift:${failingProfiles.join(',')}`);
  }
  if (clsBreaches.length > 0) {
    summary.findings.push(`deeplink-cls-breach:${clsBreaches.join(',')}`);
  }
  if (misplacedContextProfiles.length > 0) {
    summary.findings.push(`linked-context-outside-drawer:${misplacedContextProfiles.join(',')}`);
  }
  if (eagerJsBeforeOpen.length > 0) {
    summary.findings.push(`eager-js-before-open:${eagerJsBeforeOpen.length}`);
  }
  if (waterfall.lateJs.length === 0) {
    summary.findings.push('advanced-panel-never-lazy-loads');
  }
  if (summary.soak.eventLeak) {
    summary.findings.push(`runtime-handler-leak:${soak.activeDelta}`);
  }
  if (summary.soak.pulseFanOut) {
    summary.findings.push(`runtime-pulse-fanout:${soak.pulseRuns}`);
  }
  if (summary.soak.slowRefresh) {
    summary.findings.push(`runtime-refresh-slow:${soak.refreshMs}`);
  }

  summary.hints = buildHints(summary);

  console.log(JSON.stringify(summary, null, 2));
}

main().catch((error) => {
  console.error('Dashboard regression bundle failed:', error.message);
  process.exit(1);
});
