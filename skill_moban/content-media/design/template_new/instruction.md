You are producing a formal HTML presentation deck for a quarterly briefing titled "Global Renewable Energy Expansion Progress." The strategy team has already prepared the briefing outline, data snapshots, a citation catalog, and a set of usable visual assets. They now need a browser-based deck that can be opened offline, works well for projection and mobile preview, and can be delivered directly to management.

Input data is in:
- `/root/environment/data/brief/`: the briefing outline, audience notes, information priority, tone requirements, section order, and final delivery constraints
- `/root/environment/data/series/`: local numeric snapshots from public energy data sources, including global annual installed capacity, generation mix, country comparisons, and supplementary dimensions
- `/root/environment/data/assets/`: local images, marks, and supporting visual assets available for the presentation
- `/root/environment/data/sources/`: the source directory, short labels, and link mappings allowed for this briefing
- `/root/environment/deck/`: the formal presentation build entrypoint, styles, scripts, and chart-generation code
- `/services/source-registry/server.py`: the startup entrypoint for the local source registry service in the same container; it may be called but must not be modified

Your tasks
1. Based on the briefing outline, data snapshots, visual assets, and audience requirements, generate a formal HTML presentation deck that fully covers every required section and key conclusion in the briefing.
2. Management has only confirmed the content scope so far and has not yet approved the final visual direction. You must first create 3 clearly distinct single-page visual direction explorations, then converge on 1 formal presentation style for the final deck. These 3 exploration drafts must remain in the workspace for later review.
3. The formal presentation must deliver a unified visual expression appropriate for a management briefing, must not depend on external web resources, and must work for desktop projection, small-screen portrait preview, and small-screen landscape preview. See the output requirements for the specific target sizes.
4. All chart footnotes, source short labels, and citation links must exactly match the canonical results returned by the local source registry.
5. If you write temporary scripts or helper files, you must still write the correct result back into the formal build pipeline and ensure the formal entrypoint `/root/environment/deck/build_briefing.py --output /root/answer` can be run repeatedly.

Output:
- `/root/answer/presentation.html`
  - Must be a complete HTML deck that can be opened locally and does not depend on external web resources
  - Must contain 8 formal slides, and the `slide_id` order and page anchors must use this exact fixed set of values: `slide-cover`, `slide-summary`, `slide-growth`, `slide-mix`, `slide-country`, `slide-risks`, `slide-actions`, `slide-sources`
  - Must support slide navigation through keyboard arrow keys, mouse wheel, and touch swipe gestures, implemented through in-deck state transitions rather than full-page scrolling or anchor-only navigation; the implementation must genuinely handle browser input events such as `keydown`, `wheel`, and `touchstart` / `touchend`
  - Must continuously display the current page index or an equivalent progress indicator so the current position is easy to identify during projection and mobile preview; this element must be directly identifiable in the DOM using `id="progress-text"` or an equivalent `data-progress-text`
  - Except for the sources slide, any slide that uses data, judgments, or conclusions must display visible source short labels in the footer or an equivalent location and link them to the canonical links returned by the local source registry; each source marker must include `data-source-id="<source_id>"`, and you must not list sources only on the final slide
  - Text content must remain accessible in the DOM; do not export each entire slide as a single image or a full-slide canvas
  - Every formal slide must be fully visible within a single viewport, with no in-slide scrolling; each slide must retain enough body text, explanatory text, or footnote text to avoid leaving only a title and placeholder elements
- `/root/answer/presentation_manifest.json`
  - Must contain the top-level keys: `deck_title`, `slide_count`, `slides`, `data_files_used`, `asset_files_used`, `source_ids_used`, `viewport_targets`, `design_notes`
  - `slide_count` must be `8`
  - Each object in `slides` must contain the keys: `slide_id`, `title`, `primary_message`, `visuals_used`, `chart_ids`, `source_ids`
  - `viewport_targets` must cover these 5 sizes: `1920x1080`, `1280x720`, `768x1024`, `375x667`, `667x375`
  - `design_notes` must be a brief description of the overall visual direction, layout rhythm, and chart treatment principles, and must clearly record which final visual direction was selected after convergence
- `/root/answer/source_audit.json`
  - Must contain the top-level keys: `registry_endpoint`, `registry_checked`, `sources_resolved`, `slide_source_map`, `notes`
  - `registry_checked` may only be `true` or `false`; the final result must be `true`
  - `registry_endpoint` must be `http://127.0.0.1:4873`
  - Each object in `sources_resolved` must contain the keys: `source_id`, `short_label`, `canonical_url`
  - It must cover every required `source_id` for this task and map them back to the sources actually used on each slide

Notes:
- Use the outline, data, assets, and local source registry provided in the container to complete the task, and make sure the final result is reproducible.
- Before producing the final presentation, you must first complete the visual direction explorations and then settle on the formal direction. Do not skip the exploration step and jump straight to the final deck, and do not delete the exploration drafts after completing the formal deck.
- During the formal build process, you must genuinely probe the health of the local source registry and resolve the required sources one by one. The citations, short labels, links, and source mappings in the final result must match those resolved results.
- You may freely decide the chart style, layout, color, typography, motion, information distribution within sections, and use of assets, but you must preserve the real data pipeline, complete section coverage, and reviewable citations.
- Do not replace the real pipeline, and do not turn data loading, chart generation, source verification, or formal output into static placeholders, screenshots, screen recordings, hard-coded conclusions, or fabricated registry responses.
- Do not degrade the browsing experience into a table-of-contents jump page or a long scrolling page; management needs stable slide-by-slide navigation and a clear current-position indicator in actual use.
- Do not avoid the task by removing features, such as reducing the 8 formal slides to fewer pages, deleting charts, deleting the sources slide, deleting sections, removing slide navigation, or piling all content into a single long scrolling page.
- Do not modify the input data, the local source registry service, tests, dependency baselines, or any skill files.
- Do not require internet access during solve; the final result must be generated entirely from container data and local services.
