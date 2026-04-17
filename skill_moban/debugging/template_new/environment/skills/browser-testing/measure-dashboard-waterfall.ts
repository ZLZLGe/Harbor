import { chromium } from './playwright-runtime';

interface WaterfallResult {
  url: string;
  initialJs: string[];
  preClickJs: string[];
  lateJs: string[];
}

async function measureDashboardWaterfall(url: string): Promise<WaterfallResult> {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const jsOrder: string[] = [];

  page.on('response', async (response) => {
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

  await browser.close();

  return {
    url,
    initialJs,
    preClickJs,
    lateJs,
  };
}

const url = process.argv[2] || 'http://localhost:3000';

measureDashboardWaterfall(url)
  .then((result) => console.log(JSON.stringify(result, null, 2)))
  .catch((error) => {
    console.error('Dashboard waterfall measurement failed:', error.message);
    process.exit(1);
  });
