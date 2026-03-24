Use the manifest in `/root/board_packet_manifest.json` and the four source documents it references in `/root/` to assemble the final board book.

- The source files named in the manifest all share the same lowercase three-letter document suffix.
- Write the finished board book to `/root/board_book` with that same suffix.

Requirements:

- Create a new page 1 as a portrait US Letter cover page.
- The cover page must contain these exact lines:
  - `April 2026 Board Book`
  - `Harbor Transit Holdings Board of Directors`
  - `Meeting Date: 2026-04-18`
  - `Meeting Time: 09:00 CST`
  - `Location: Bund Conference Room 7A`
  - `Confidential Board Materials`
- Before each section listed in the manifest, insert a new portrait US Letter divider page.
- Each divider page must contain these exact lines:
  - `Section <section_code>`
  - the matching `section_title`
  - `Confidential Board Materials`
- For every `items` entry in each section, copy only the listed 1-based pages from the named source file and keep them in the listed order.
- Keep copied source pages unchanged, including their original page size and orientation.
- Do not include any source page that is not listed in the manifest.
- The final page order must be:
  - cover page
  - divider for section A, then that section's listed source pages
  - divider for section B, then that section's listed source pages
  - divider for section C, then that section's listed source pages
