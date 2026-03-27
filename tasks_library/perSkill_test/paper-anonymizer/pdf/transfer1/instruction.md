Build a short review packet by merging one page from each PDF.

Inputs:
- `/root/paper1.pdf`
- `/root/paper2.pdf`
- `/root/paper3.pdf`

Create:
1. `/root/output/transfer1_packet.pdf`
2. `/root/reports/transfer1_packet_index.json`

Rules:
- The packet must contain exactly 3 pages.
- Page order must be:
  1. page 1 of `paper1.pdf`
  2. page 1 of `paper2.pdf`
  3. page 1 of `paper3.pdf`
- The JSON index must contain an array key `pages` with 3 entries, each including:
  - `packet_page`
  - `source_file`
  - `source_page`
