有声书项目的上游处理已经完成。输入文件 `/root/audiobook_dialogue_segments.json` 按章节给出了对白片段、章节编号、片段边界和对应声纹 embedding；其中还夹带了少量 `role_hint = narration` 的旁白片段，它们只是干扰项，不应进入最终台账。

请完成以下目标：

1. 读取 `/root/audiobook_dialogue_segments.json`，只对 `role_hint` 为 `dialogue` 的片段做全局聚类。
2. 跨章节识别稳定声线组；同一角色声线在不同章节里必须得到同一个 `voice_cast_id`。
3. 严格按照输入里的 `voice_cast_id_rule` 命名 `voice_cast_00`、`voice_cast_01` 这类稳定编号。
4. 将结果写入 `/root/voice_cast_ledger.csv`。

输出 CSV 必须使用下面这组表头，顺序不能变：

`row_type,book_id,voice_cast_id,chapter_id,chapter_number,segment_id,start_sec,end_sec,duration_sec,chapter_count,segment_count,total_dialogue_duration_sec,first_chapter_number,transcript_excerpt`

写出规则：

- 先写所有 `cast_summary` 行，再写所有 `segment_detail` 行。
- `cast_summary` 行按 `voice_cast_id` 升序排序。
- `segment_detail` 行按 `chapter_number`、`start_sec` 升序排序。
- `cast_summary` 行必须聚合该声线组全部对白片段，并填写：
  - `chapter_count`
  - `segment_count`
  - `total_dialogue_duration_sec`
  - `first_chapter_number`
  - `transcript_excerpt`：该声线组第一次出现的对白摘录
- `segment_detail` 行必须覆盖全部对白片段，并填写每段的：
  - `chapter_id`
  - `chapter_number`
  - `segment_id`
  - `start_sec`
  - `end_sec`
  - `duration_sec`
  - `transcript_excerpt`
- 不属于当前行语义的列请留空。
- 所有时长和时间字段统一保留两位小数。
- 旁白片段不得出现在输出 CSV 中。
