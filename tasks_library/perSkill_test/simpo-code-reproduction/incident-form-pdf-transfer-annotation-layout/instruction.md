请阅读 `/root/incident_packet/` 下名为 `terminal_incident_form` 的事故表单文档，以及 `/root/incident_packet/response_payload.json`，生成 `/root/incident_fields.json`。

这份表单文档是静态页面，不包含可直接回填的表单字段。你需要先把它渲染成逐页图像，再根据页面内容人工定位标签区和填写区，最后输出一个 JSON 对象，格式如下：

```json
{
  "pages": [
    {
      "page_number": 1,
      "image_width": 772,
      "image_height": 1000
    }
  ],
  "form_fields": [
    {
      "page_number": 1,
      "description": "Write the incident ID",
      "field_label": "Incident ID",
      "label_bounding_box": [72, 116, 160, 138],
      "entry_bounding_box": [214, 116, 402, 138],
      "entry_text": {
        "text": "<copy from response_payload.json>",
        "font_size": 14,
        "font_color": "000000"
      }
    }
  ]
}
```

要求：

1. `pages` 必须包含全部 2 页，并填写你实际分析时所用页面图像的真实宽高。
2. `form_fields` 必须恰好覆盖下面 11 个写入目标，不要多写，也不要漏写：
   - `Write the incident ID`
   - `Write the date of event`
   - `Write the reported time`
   - `Write the vehicle and route`
   - `Write the intersection or stop`
   - `Write the brief event summary`
   - `Mark the No checkbox for medical evaluation needed`
   - `Mark the Yes checkbox for supervisor notified before shift end`
   - `Mark the Yes checkbox for photos attached`
   - `Write the reviewer name`
   - `Write the corrective action due date`
3. 每个字段都必须包含 `page_number`、`description`、`field_label`、`label_bounding_box`、`entry_bounding_box`、`entry_text`，且 `entry_text` 必须显式包含 `text`、`font_size`、`font_color` 三个字段。
4. 所有边界框都使用页面图像坐标，格式固定为 `[left, top, right, bottom]`，原点在左上角。
5. `label_bounding_box` 需要覆盖对应可见标签文字；`entry_bounding_box` 只能覆盖实际填写区域，不能把已有标签文字框进去。
6. `label_bounding_box` 与 `entry_bounding_box` 不能相交，`entry_bounding_box` 也不能和其他字段的标签框或填写框相交。
7. 复选项只给实际需要勾选的那个小方框建字段，并把 `entry_text.text` 写成 `X`。
8. 文本内容必须来自 `response_payload.json`。不要改写大小写、标点或日期格式。
9. 评测会按渲染后的页面图像检查框位。标签框和填写框如果与目标区域偏差超过 12 像素，会被判定为不合格。
10. 评测还会用你的 JSON 回写生成带注释版文档，所以填写框必须足够容纳对应文本。
11. 不要修改输入表单文档或输入 JSON。
