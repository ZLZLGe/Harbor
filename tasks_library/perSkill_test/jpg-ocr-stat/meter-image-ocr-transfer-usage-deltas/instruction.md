## 任务说明

`/app/workspace/meter_photos/` 下有 5 张现场抄表图片。每张图都包含一次采集日期和一个累计表盘读数，同时还会出现 `ZONE`、`SHIFT` 等无关数字。

请读取该目录中的全部图片，识别每张图里的日期与表盘读数，并按日期升序生成 `/app/workspace/meter_consumption.json`。

输出文件必须是一个 JSON 对象，且顶层只能包含以下两个字段：

```json
{
  "readings": [
    {
      "filename": "源图片文件名",
      "date": "YYYY-MM-DD",
      "reading": "保留一位小数的字符串",
      "delta_from_previous": null
    }
  ],
  "total_consumption": "保留一位小数的字符串"
}
```

具体要求：

- `readings` 必须覆盖目录中的全部图片，每张图恰好对应 1 条记录。
- `readings` 中的记录必须按 `date` 升序排列，而不是按文件名排序。
- `date` 必须统一写成 `YYYY-MM-DD`。
- `reading` 必须是十进制字符串，并保留 1 位小数，例如 `1842.7`。
- 第一条记录的 `delta_from_previous` 必须是 `null`。
- 从第二条记录开始，`delta_from_previous` 必须等于当前 `reading` 减去上一条 `reading` 的结果，并保留 1 位小数。
- `total_consumption` 必须等于最后一次读数减去第一次读数，且保留 1 位小数。
- 不要输出额外的顶层字段，也不要在每条记录里添加额外字段。

提示：

- 日期行附近通常有 `DATE`。
- 读数行附近通常有 `READ`。
- 日期分隔符可能是 `/` 或 `-`。
- 注意忽略 `ZONE`、`SHIFT` 等与表盘读数无关的数字。
