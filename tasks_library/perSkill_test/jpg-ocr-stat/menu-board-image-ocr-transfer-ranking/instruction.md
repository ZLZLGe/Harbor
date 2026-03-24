## Task Description

In `/app/workspace/menu_boards`, I provide a folder of cafe menu board images.

Each image shows one board with several menu items and their prices. Read every image in that directory and write `/app/workspace/menu_price_report.md`.

The report must use this exact high-level structure:

```md
# Menu Price Report

## <board filename>
| item | price |
| --- | --- |
| ... | ... |
Cheapest item: <item> | <price>

## <next board filename>
...

## Summary
Total items: <count>
Overall median price: <price>
```

Detailed requirements:

- Create one `##` section for each input image, ordered by filename ascending.
- In each board section, include exactly one Markdown table with the columns `item` and `price`.
- Each table row must contain one extracted menu item and its price.
- Within each board section, order rows by `price` ascending. If two prices are equal, order those rows by `item` ascending.
- Write prices as plain decimal strings with exactly two digits after the decimal point.
- After each table, add a line `Cheapest item: <item> | <price>` using the cheapest row from that same board.
- In the final `## Summary` section, `Total items` must equal the total number of extracted menu rows across all boards.
- `Overall median price` must be the median price across all extracted menu items from all boards combined.

Do not add extra sections, extra columns, or additional output files.

## Hints

- Menu titles, subtitles, and notes also appear in the images; they are not menu items.
- Prices appear as decimal values such as `4.85` or `7.60`.
- A board may contain several beverage or food names written in uppercase.
- The verifier will check both the extracted rows and the computed summary values.
