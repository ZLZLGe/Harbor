Split the first four pages of `/root/paper1.pdf` into individual files.

Create these outputs:
- `/root/output/transfer2_pages/page_001.pdf`
- `/root/output/transfer2_pages/page_002.pdf`
- `/root/output/transfer2_pages/page_003.pdf`
- `/root/output/transfer2_pages/page_004.pdf`
- `/root/reports/transfer2_split_manifest.csv`

Manifest CSV requirements:
- Header: `page_index,output_file,char_count`
- Exactly 4 data rows, one per output page
- `page_index` must be 1..4
- `output_file` must match the generated file name
- `char_count` must be positive
