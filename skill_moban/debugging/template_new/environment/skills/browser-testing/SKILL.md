---
name: browser-testing
description: "VERIFY your changes work. Measure dashboard waterfalls, deep-link stability, and long-session interaction behavior before and after changes. Includes ready-to-run scripts: measure.ts, measure-cls.ts, measure-dashboard-waterfall.ts, measure-dashboard-deeplink.ts, and measure-dashboard-soak.ts"
---

# Browser Measurement with Playwright CDP

Diagnose runtime issues by measuring actual load times, code-loading behavior, visual stability, and long-session degradation in a real browser.

**The browser-testing toolkit is pre-installed with this skill.** Use the scripts in this skill directory before and after changing code.

## Quick Start

```bash
# Measure a page and capture its network waterfall
tsx <path-to-this-skill>/measure.ts http://localhost:3000

# Measure an API endpoint directly
tsx <path-to-this-skill>/measure.ts http://localhost:3000/api/dashboard
```

The script outputs JSON with:

```json
{
  "url": "http://localhost:3000",
  "totalMs": 1523,
  "requests": [
    { "url": "http://localhost:3000/", "ms": 45.2 },
    { "url": "http://localhost:3000/_next/static/chunks/app/page.js", "ms": 301.1 }
  ],
  "metrics": {
    "JSHeapUsedSize": 4521984,
    "LayoutCount": 12,
    "ScriptDuration": 0.234
  }
}
```

### What to watch

| Symptom | Likely cause | Fix direction |
|---------|--------------|---------------|
| Large initial JS before advanced insights is opened | Advanced code imported eagerly | Split with `dynamic()` or defer imports |
| Layout shift after first paint | Hydration drift, unstable filter restoration, or missing reserved space | Align initial state and reserve space |
| Requests only appear after one another | Serialized fetches or blocked responses | Start requests earlier and await later |
| Repeated actions get slower over time | Listener leaks, observer leaks, repeated subscriptions | Add cleanup and narrow effect dependencies |
| High `LayoutCount` or `ScriptDuration` | Components or handlers doing too much work | Reduce rerenders and handler fan-out |

## Visual Stability Measurement

```bash
tsx <path-to-this-skill>/measure-cls.ts http://localhost:3000
```

Output:

```json
{
  "url": "http://localhost:3000",
  "cls": 0.42,
  "rating": "poor",
  "shifts": [
    {
      "value": 0.15,
      "hadRecentInput": false
    }
  ]
}
```

### CLS thresholds

| CLS score | Rating | Action |
|-----------|--------|--------|
| < 0.1 | Good | No action needed |
| 0.1 - 0.25 | Needs Improvement | Review shift sources |
| > 0.25 | Poor | Fix immediately |

For more accurate measurement:

```bash
# Basic measurement
tsx <path-to-this-skill>/measure-cls.ts http://localhost:3000

# With scrolling to catch below-the-fold shifts
tsx <path-to-this-skill>/measure-cls.ts http://localhost:3000 --scroll
```

## Dashboard Waterfall Checks

For this dashboard task, confirm that advanced insights really stays out of the critical path until the user opens it:

```bash
tsx <path-to-this-skill>/measure-dashboard-waterfall.ts \
  "http://localhost:3000"
```

Output:

```json
{
  "url": "http://localhost:3000",
  "initialJs": ["http://localhost:3000/_next/static/chunks/app/page.js"],
  "preClickJs": ["http://localhost:3000/_next/static/chunks/app/page.js"],
  "lateJs": ["http://localhost:3000/_next/static/chunks/app/components/AdvancedInsightsPanel.js"]
}
```

If `preClickJs` grows after the idle wait, you still have eager loading.

## Repeated Interaction Checks

Some bugs only appear after many clicks or tab switches. When that happens:

```bash
tsx <path-to-this-skill>/measure-dashboard-soak.ts \
  "http://localhost:3000"
```

Output:

```json
{
  "url": "http://localhost:3000",
  "activeDelta": 34,
  "pulseRuns": 57,
  "refreshMs": 411
}
```

### Cold-start deep-link checks

When the report mentions a wrong or unstable first-load state, reproduce it with a stale local session already present. On this dashboard, run the same linked alert through both the phone and tablet profiles because the visual shift can be breakpoint-sensitive even after the wrong-filter bug is fixed:

```bash
tsx <path-to-this-skill>/measure-dashboard-deeplink.ts \
  "http://localhost:3000/?filter=north-america&alert=retention-drop-na"
```

Output:

```json
{
  "url": "http://localhost:3000/?filter=north-america&alert=retention-drop-na",
  "profiles": [
    {
      "name": "iphone-13",
      "label": "Europe",
      "drawerTitle": "Retention drop in North America",
      "linkedContextText": null,
      "linkedContextInDrawer": false,
      "cls": 0.118
    },
    {
      "name": "tablet-820",
      "label": "North America",
      "drawerTitle": "Retention drop in North America",
      "linkedContextText": "Linked alert context: ... North America ...",
      "linkedContextInDrawer": false,
      "cls": 0.081
    }
  ]
}
```

Do not stop after a single interaction when the bug is described as “gets worse over time”, and do not trust archived evidence over a fresh browser reproduction. On this task specifically, the soak script is the shortest path to the long-session regression and the deep-link script is the shortest path to the cold-start drift plus breakpoint-specific CLS plus linked-context misplacement.
