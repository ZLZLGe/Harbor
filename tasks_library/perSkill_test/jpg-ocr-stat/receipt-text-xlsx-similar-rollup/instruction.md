## 任务说明

`/app/workspace/inbox/receipts_txt/` 目录下提供了一组按文件名编号的 OCR 文本小票，每个文件对应一张已经识别成纯文本的小票内容。请读取该目录下的所有 `.txt` 文件，抽取每张小票的交易日期与总金额，并覆盖 `/app/workspace/` 根目录中已经放好的目标工作簿文件；目标文件主文件名为 `receipt_rollup`。

输出要求如下：

- 工作簿中只能保留一个工作表，工作表名必须是 `results`
- 列严格为 `filename`、`date`、`total_amount`
- 第一行必须是表头
- 数据行必须按文件名升序排列
- `date` 写成 `YYYY-MM-DD`
- `total_amount` 写成保留两位小数的文本，不要带千分位分隔符
- 如果某个字段无法确认，对应单元格留空
- 不要生成额外的工作表、列或说明内容

这些文本来自 OCR 结果，格式不完全统一。日期和总金额可能出现在不同位置，总金额也可能出现在关键词下一行。常见总金额关键词包括 `GRAND TOTAL`、`TOTAL RM`、`TOTAL AMOUNT`、`AMOUNT DUE`、`NETT TOTAL`、`TOTAL DUE`。同时要避免把 `SUBTOTAL`、`TAX`、`CHANGE` 等非最终金额误写进去。
