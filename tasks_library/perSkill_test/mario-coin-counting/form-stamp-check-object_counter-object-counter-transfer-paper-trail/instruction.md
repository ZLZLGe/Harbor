你会在 `/root/form_pages/` 找到 4 张按页码顺序命名的灰度扫描表单页：

- `/root/form_pages/page_001.pgm`
- `/root/form_pages/page_002.pgm`
- `/root/form_pages/page_003.pgm`
- `/root/form_pages/page_004.pgm`

你还会在 `/root/markup_refs/` 找到 3 张标记模板图：

- `/root/markup_refs/paid_stamp.pgm`
- `/root/markup_refs/review_stamp.pgm`
- `/root/markup_refs/warning_sticker.pgm`

请统计每一页里这三类标记各出现了多少次，并把结果写入 `/root/form_markup_counts.tsv`。

输出要求：

1. 输出必须是制表符分隔的 TSV 文件。
2. 表头必须严格为 `page_id	page_file	paid_stamps	review_stamps	warning_stickers	total_markups`。
3. 数据行顺序必须固定为 `page_001`、`page_002`、`page_003`、`page_004`。
4. `page_file` 列必须填写对应页面图像的绝对路径。
5. `total_markups` 必须等于该页三类标记数量之和。
6. 文件末尾还必须追加一行汇总，格式为 `TOTAL	ALL_PAGES	<paid 总数>	<review 总数>	<warning 总数>	<全部标记总数>`。
7. 不要输出额外列、额外行或解释文字。
