Repair the design review presentation at `/root/Design-Review-Deck.pptx` using the final review data in `/root/design_review_updates.json`.

Requirements:
- The deck already contains stale speaker notes. Replace the existing speaker notes on every slide listed in the JSON `notes` object.
- Each speaker-notes paragraph in the output must exactly match the corresponding strings and order from the JSON file.
- The deck also contains outdated reviewer comments. Replace the existing reviewer comments on every slide listed in the JSON `comments` array.
- Use the reviewer name and initials from the JSON data.
- Place each reviewer comment near the labeled slide element named by `target_label`.
- Keep all visible content on the original slides unchanged.
- Append exactly one new slide at the end titled `Action Items`.
- On the new slide, add one bulleted line per entry in `action_items`, formatted exactly as `<owner>: <decision>`.
- Do not add extra slides or reorder the original slides.

Save the finished presentation to `/root/Design-Review-Commented.pptx`.
