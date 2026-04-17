import { createRequire } from 'node:module';

const requireFromSkillToolkit = createRequire(import.meta.url);

export const { chromium, devices } = requireFromSkillToolkit('/opt/browser-testing/node_modules/playwright') as typeof import('playwright');
