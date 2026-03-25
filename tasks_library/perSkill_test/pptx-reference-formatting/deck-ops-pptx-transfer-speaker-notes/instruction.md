Prepare the webinar rehearsal deck in `/root/` with filename `Webinar-Rehearsal` and its existing presentation-file extension, using `/root/speaker_notes.json`.

- For each slide number listed in the JSON `slides` object, make sure that slide has speaker notes.
- If a listed slide already has speaker notes, replace the old notes instead of appending to them.
- Each targeted notes page must contain exactly one title paragraph first, using the JSON `title` string.
- After the title, add one paragraph per entry in the JSON `bullets` array, in the same order, using real PowerPoint bullet formatting.
- Only the slide numbers listed in the JSON should have speaker notes in the final deck.
- Keep the visible slide content and slide order unchanged.

Save the finished deck in `/root/` with filename `Webinar-Rehearsal-notes-ready` and the same presentation-file extension as the input deck.
