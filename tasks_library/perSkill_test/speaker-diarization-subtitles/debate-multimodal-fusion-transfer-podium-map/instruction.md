你会拿到一组已经整理好的辩论讲台证据文件：

- `/root/speech_segments.csv`
- `/root/podium_motion_windows.json`
- `/root/cluster_slot_affinity.json`
- `/root/stage_layout.json`

请基于这些输入生成 `/root/podium_speaking_times.csv`。

输出必须是 UTF-8 编码的 CSV，表头固定为：

`row_type,slot_id,segment_id,start_sec,end_sec,duration_sec,assignment_basis,total_speaking_sec,speaking_turns`

结果必须满足以下约束：

1. 先写完所有 `segment` 行，再写所有 `summary` 行。
2. `segment` 行必须与 `speech_segments.csv` 中的片段一一对应，不能新增或删除片段，并按 `start_sec` 升序排列。
3. `summary` 行必须与 `stage_layout.json` 中的 `slots` 一一对应，并按 `display_order` 升序排列。
4. `slot_id` 只能使用 `stage_layout.json` 中出现过的固定讲台位置。
5. 所有时间与时长字段都要保留两位小数。

`segment` 行字段要求：

- `row_type`: 固定写 `segment`
- `slot_id`: 该片段归属的讲台位置
- `segment_id`: 必须来自 `speech_segments.csv`
- `start_sec`: 必须等于输入片段开始时间
- `end_sec`: 必须等于输入片段结束时间
- `duration_sec`: 必须等于 `end_sec - start_sec`
- `assignment_basis`: 只能是 `visual_lip_motion` 或 `audio_cluster_fallback`
- `total_speaking_sec`: 留空
- `speaking_turns`: 留空

`summary` 行字段要求：

- `row_type`: 固定写 `summary`
- `slot_id`: 对应的讲台位置
- `segment_id`、`start_sec`、`end_sec`、`duration_sec`、`assignment_basis`: 全部留空
- `total_speaking_sec`: 该 `slot_id` 下所有 `segment` 行的 `duration_sec` 之和
- `speaking_turns`: 该 `slot_id` 下所有 `segment` 行的数量

片段归因规则：

1. 对每个语音片段，计算它与 `podium_motion_windows.json` 中每个 window 的时间重叠。
2. 对每个 `slot_id`，把所有重叠 window 中该 slot 出现在 `lip_motion_slots` 里的重叠时长累加，得到该 slot 的 `lip_motion_overlap_sec`。
3. 如果某个 slot 的 `lip_motion_overlap_sec` 同时满足：
   - 是所有 slot 中的严格最大值；
   - 且 `lip_motion_overlap_sec / 片段时长 >= 0.50`
   那么该片段归给这个 slot，并把 `assignment_basis` 写成 `visual_lip_motion`。
4. 否则，回退到 `cluster_slot_affinity.json`：
   - 读取该片段 `audio_cluster` 对各个 slot 的分数；
   - 选择分数最高的 slot；
   - `assignment_basis` 写成 `audio_cluster_fallback`。
5. 最终 summary 统计只能基于你输出的 `segment` 行聚合得到。
