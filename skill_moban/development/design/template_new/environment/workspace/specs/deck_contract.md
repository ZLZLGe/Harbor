# Deck Contract

The final deliverable is a browser-native HTML deck at `/app/output/deck/index.html`.

## Rendering contract

- Target viewport: `1440x900`
- Secondary safety viewport: `1280x720`
- The deck must remain legible at both viewports without requiring vertical scroll to reveal primary content.
- Rendering must be offline-safe. Do not depend on remote fonts, remote CSS, remote JS, remote images, or external iframes.

## Slide contract

- Exactly 6 slides are required.
- The six slides must cover, in order:
  1. cover and core takeaway
  2. KPI overview
  3. comparison story
  4. evidence or scenario grounding
  5. journey or concept diagram
  6. risks, boundaries, and next steps
- Each slide must remain individually addressable inside the deck and must expose a visible title.

## Navigation contract

- The deck must support keyboard navigation via `ArrowRight` / `ArrowLeft`.
- A visible active-slide indicator or equivalent progress marker must exist.
- Critical content may not be hidden behind hover-only interactions.

## Visual-component contract

- The `kpi-overview` slide must include at least one structured data graphic rendered via `svg`, `canvas`, or a repeated bar / point DOM pattern. A single static screenshot is not sufficient.
- The KPI graphic must remain auditable against the frozen KPI source. The QA chain will inspect whether the rendered story still preserves machine-readable ties back to the underlying KPI data.
- The KPI slide should also expose machine-readable metric summaries for the primary launch-readiness signals shown in the deck.
- The `comparison` slide must stay grounded in `/app/workspace/data/feature_matrix.csv`. The QA chain will verify that the rendered matrix still reflects the frozen capability table.
- The `evidence` and `risks-next-steps` slides must remain traceable to the approved quote payload. Quote blocks should carry stable provenance rather than only freeform prose.
- The `journey-diagram` slide must include a structured workflow or concept diagram rendered via `svg`, `canvas`, or repeated node / edge DOM elements. A pasted raster image is not sufficient.
- The journey diagram must remain auditable against `/app/workspace/data/user_journey.json`. The QA chain will verify that the workflow still covers the intended stages and handoffs.
- The final deck must explicitly acknowledge at least one real launch boundary from the brief or approved evidence payload. Do not present the story as an unlimited platform claim.

## Source-trace contract

- The final submission payload must preserve per-slide traceability back to real inputs under `/app/workspace/...`.
- The KPI story must remain auditable against `/app/workspace/data/weekly_kpis.csv`.
- The journey story must remain auditable against `/app/workspace/data/user_journey.json`.
- Visible source labels in the HTML should expose machine-readable source markers so packaging and QA tools can reconstruct per-slide traceability without hardcoding visible copy.
- Structured chart marks, comparison rows, quote blocks, and journey nodes or edges should also preserve machine-readable source linkage for high-signal claims.
- Exact packaging conventions are determined by the live localhost `manifest -> validate` chain. If a task-local skill is available, use it to standardize diagnosis and packaging.

## Submission contract

- The final payload at `/app/output/deck_submission.json` must be the real JSON submission sent through the live localhost validator for the final deck.
- The final receipt at `/app/output/deck_receipt.json` must be the real validator response returned by `POST /validate`.
- Exact field-level packaging and receipt details are intentionally defined by the live `manifest -> validate` chain rather than fully spelled out here.
