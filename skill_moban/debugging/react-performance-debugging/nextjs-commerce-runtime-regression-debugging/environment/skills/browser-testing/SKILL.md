---
name: browser-testing
description: "VERIFY your changes work. Measure network waterfalls, cold-start review stability, and repeated interaction behavior before and after changes. Includes ready-to-run scripts: measure.ts, measure-cls.ts, measure-review-entry.ts, and measure-interactions.ts"
---

# Browser Measurement with Playwright CDP

Diagnose runtime issues by measuring actual load times, code-loading behavior, and visual stability in a real browser.

**Playwright is pre-installed.** Use the scripts in this skill directory before and after changing code.

## Quick Start

```bash
# Measure a page and capture its network waterfall
npx tsx <path-to-this-skill>/measure.ts http://localhost:3000

# Measure an API endpoint directly
npx tsx <path-to-this-skill>/measure.ts http://localhost:3000/api/books
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
| Large initial JS before any advanced UI is opened | Advanced code imported eagerly | Split with `dynamic()` or defer imports |
| Layout shift after first paint | Hydration drift, unstable state, or missing reserved space | Align initial state and reserve space |
| Requests only appear after one another | Serialized fetches or blocked responses | Start requests earlier and await later |
| Repeated actions get slower over time | Listener leaks, observer leaks, repeated subscriptions | Add cleanup and narrow effect dependencies |
| High `LayoutCount` or `ScriptDuration` | Components or handlers doing too much work | Reduce rerenders and handler fan-out |

## Visual Stability Measurement

```bash
npx tsx <path-to-this-skill>/measure-cls.ts http://localhost:3000
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
npx tsx <path-to-this-skill>/measure-cls.ts http://localhost:3000

# With scrolling to catch below-the-fold shifts
npx tsx <path-to-this-skill>/measure-cls.ts http://localhost:3000 --scroll
```

## Repeated Interaction Checks

Some bugs only appear after many clicks or tab switches. When that happens:

```bash
npx tsx <path-to-this-skill>/measure-interactions.ts \
  "http://localhost:3000/?shelf=category-classics-of-literature"
```

Output:

```json
{
  "url": "http://localhost:3000/?shelf=category-classics-of-literature",
  "activeDelta": 34,
  "probeRuns": 57
}
```

### Cold-start review entry checks

When the report mentions a wrong or unstable first-load state, reproduce it with a stale local session already present:

```bash
npx tsx <path-to-this-skill>/measure-review-entry.ts \
  "http://localhost:3000/?shelf=category-romance"
```

Output:

```json
{
  "url": "http://localhost:3000/?shelf=category-romance",
  "label": "Gothic Fiction",
  "cls": 0.118,
  "console": [
    "Persisted review context is overriding the live review entry."
  ]
}
```

Do not stop after a single interaction when the bug is described as “gets worse over time”, and do not trust archived evidence over a fresh browser reproduction.
